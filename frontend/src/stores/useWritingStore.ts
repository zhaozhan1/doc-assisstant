import { create } from "zustand";
import type {
  GenerationRequest,
  PptxRequest,
  PptxResult,
  UnifiedSearchResult,
} from "../types/api";
import * as generationApi from "../api/generation";
import { parseSSEStream } from "../utils/sse";

export type WritingMode = "onestep" | "stepbystep" | "wordtoppt";

interface WritingState {
  mode: WritingMode;
  content: string;
  outputPath: string | null;
  isStreaming: boolean;
  error: string | null;
  selectedRefs: string[];
  searchResults: UnifiedSearchResult[];
  pptxTaskId: string | null;
  pptxResult: PptxResult | null;
  pptxError: string | null;
  isGeneratingPptx: boolean;
  sessionGeneratedDocs: string[];
}

interface WritingActions {
  generate: (request: GenerationRequest) => Promise<void>;
  startStream: (request: GenerationRequest) => Promise<void>;
  abortStream: () => void;
  setSelectedRefs: (refs: string[]) => void;
  setSearchResults: (results: UnifiedSearchResult[]) => void;
  setMode: (mode: WritingMode) => void;
  startPptxGeneration: (request: PptxRequest) => Promise<void>;
  resetPptxState: () => void;
  addSessionDoc: (path: string) => void;
}

export const useWritingStore = create<WritingState & WritingActions>(
  (set) => {
    let abortController: AbortController | null = null;

    return {
      mode: "onestep",
      content: "",
      outputPath: null,
      isStreaming: false,
      error: null,
      selectedRefs: [],
      searchResults: [],
      pptxTaskId: null,
      pptxResult: null,
      pptxError: null,
      isGeneratingPptx: false,
      sessionGeneratedDocs: [],

      generate: async (request: GenerationRequest) => {
        set({ isStreaming: true, error: null });
        try {
          const result = await generationApi.generate(request);
          set({
            content: result.content,
            outputPath: result.output_path,
            isStreaming: false,
          });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : "生成失败",
            isStreaming: false,
          });
        }
      },

      startStream: async (request: GenerationRequest) => {
        abortController?.abort();
        set({ content: "", isStreaming: true, error: null });

        const controller = new AbortController();
        abortController = controller;

        try {
          const response = await fetch("/api/generation/generate/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request),
            signal: controller.signal,
          });

          if (!response.ok) {
            throw new Error(
              `请求失败: ${response.status} ${response.statusText}`,
            );
          }

          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error("无法读取响应流");
          }

          for await (const token of parseSSEStream(reader)) {
            set((state) => ({ content: state.content + token }));
          }

          set({ isStreaming: false });
        } catch (err: unknown) {
          if (err instanceof DOMException && err.name === "AbortError") {
            set({ isStreaming: false });
            return;
          }
          set({
            error: err instanceof Error ? err.message : "流式生成失败",
            isStreaming: false,
          });
        }
      },

      abortStream: () => {
        abortController?.abort();
        set({ isStreaming: false });
      },

      setSelectedRefs: (refs: string[]) => set({ selectedRefs: refs }),
      setSearchResults: (results: UnifiedSearchResult[]) =>
        set({ searchResults: results }),
      setMode: (mode: WritingMode) => set({ mode }),

      startPptxGeneration: async (request: PptxRequest) => {
        set({ pptxResult: null, pptxError: null, isGeneratingPptx: true });
        try {
          const { task_id } = await generationApi.generatePptx(request);
          set({ pptxTaskId: task_id });

          const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
          const ws = new WebSocket(
            `${protocol}//${window.location.host}/ws/pptx-tasks/${task_id}`,
          );
          ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "completed") {
              set({ pptxResult: msg.data, isGeneratingPptx: false });
              ws.close();
            } else if (msg.type === "failed") {
              set({ pptxError: msg.data.error || "生成失败", isGeneratingPptx: false });
              ws.close();
            } else {
              set({ pptxResult: msg.data });
            }
          };
          ws.onerror = () => {
            set({ pptxError: "WebSocket 连接失败", isGeneratingPptx: false });
          };
        } catch (err) {
          set({
            pptxError: err instanceof Error ? err.message : "PPT 生成失败",
            isGeneratingPptx: false,
          });
        }
      },

      resetPptxState: () =>
        set({ pptxTaskId: null, pptxResult: null, pptxError: null, isGeneratingPptx: false }),

      addSessionDoc: (path: string) =>
        set((state) => ({
          sessionGeneratedDocs: [...state.sessionGeneratedDocs, path],
        })),
    };
  },
);
