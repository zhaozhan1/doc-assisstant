import { useState, useRef, useCallback } from "react";
import type { GenerationRequest } from "../types/api";
import { parseSSEStream } from "../utils/sse";

export function useSSE() {
  const [content, setContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (request: GenerationRequest) => {
    // Abort any previous stream
    abortRef.current?.abort();

    setContent("");
    setError(null);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

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
        setContent((prev) => prev + token);
      }

      setIsStreaming(false);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // Aborted by user, not an error
        setIsStreaming(false);
        return;
      }
      setError(
        err instanceof Error ? err.message : "流式生成失败",
      );
      setIsStreaming(false);
    }
  }, []);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return { content, isStreaming, error, start, abort };
}
