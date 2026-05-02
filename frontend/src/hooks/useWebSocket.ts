import { useState, useRef, useCallback, useEffect } from "react";
import type { TaskProgress } from "../types/api";

type WSStatus = "idle" | "connected" | "completed" | "error";

interface WSMessage {
  type: "progress" | "completed" | "error";
  data: TaskProgress | Record<string, unknown>;
}

export function useWebSocket() {
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [status, setStatus] = useState<WSStatus>("idle");
  const wsRef = useRef<WebSocket | null>(null);

  const close = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(
    (taskId: string) => {
      close();

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws/tasks/${taskId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        setStatus("connected");
      });

      ws.addEventListener("message", (event: MessageEvent) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          if (msg.type === "progress") {
            setProgress(msg.data as TaskProgress);
          } else if (msg.type === "completed") {
            setProgress(msg.data as TaskProgress);
            setStatus("completed");
            ws.close();
          } else if (msg.type === "error") {
            setStatus("error");
          }
        } catch {
          // Ignore malformed messages
        }
      });

      ws.addEventListener("error", () => {
        setStatus("error");
      });
    },
    [close],
  );

  const cancel = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "cancel" }));
    }
  }, []);

  useEffect(() => {
    return () => {
      close();
    };
  }, [close]);

  return { progress, status, connect, cancel };
}
