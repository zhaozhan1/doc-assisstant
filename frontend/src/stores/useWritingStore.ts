import { create } from "zustand";
import type {
  GenerationRequest,
  UnifiedSearchResult,
} from "../types/api";
import * as generationApi from "../api/generation";

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

interface SSEMessage {
  token: string;
}

export const useWritingStore = create<WritingState & WritingActions>(
  (set, get) => {
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

          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const payload = line.slice(6).trim();
                if (payload === "[DONE]") {
                  set({ isStreaming: false });
                  return;
                }
                try {
                  const parsed = JSON.parse(payload) as SSEMessage;
                  if (parsed.token) {
                    set({ content: get().content + parsed.token });
                  }
                } catch {
                  // Skip malformed lines
                }
              }
            }
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
