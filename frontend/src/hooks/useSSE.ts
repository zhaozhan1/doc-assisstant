import { useState, useRef, useCallback } from "react";
import type { GenerationRequest } from "../types/api";

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

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE lines
        const lines = buffer.split("\n");
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") {
              setIsStreaming(false);
              return;
            }
            try {
              const parsed = JSON.parse(payload) as { token: string };
              if (parsed.token) {
                setContent((prev) => prev + parsed.token);
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
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
