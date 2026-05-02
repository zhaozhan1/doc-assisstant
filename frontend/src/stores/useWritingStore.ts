import { create } from "zustand";
import type {
  GenerationRequest,
  UnifiedSearchResult,
} from "../types/api";
import * as generationApi from "../api/generation";
import { parseSSEStream } from "../utils/sse";

export type WritingMode = "onestep" | "stepbystep" | "wordtoppt";

interface WritingState {
  mode: WritingMode;
  content: string;
  isStreaming: boolean;
  error: string | null;
  selectedRefs: string[];
  searchResults: UnifiedSearchResult[];
}

interface WritingActions {
  generate: (request: GenerationRequest) => Promise<void>;
  startStream: (request: GenerationRequest) => Promise<void>;
  abortStream: () => void;
  setSelectedRefs: (refs: string[]) => void;
  setSearchResults: (results: UnifiedSearchResult[]) => void;
  setMode: (mode: WritingMode) => void;
}

export const useWritingStore = create<WritingState & WritingActions>(
  (set) => {
    let abortController: AbortController | null = null;

    return {
      mode: "onestep",
      content: "",
      isStreaming: false,
      error: null,
      selectedRefs: [],
      searchResults: [],

      generate: async (request: GenerationRequest) => {
        set({ isStreaming: true, error: null });
        try {
          const result = await generationApi.generate(request);
          set({ content: result.content, isStreaming: false });
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
    };
  },
);
