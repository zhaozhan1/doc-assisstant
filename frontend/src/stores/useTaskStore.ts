import { create } from "zustand";
import type { TaskProgress } from "../types/api";
import * as filesApi from "../api/files";

interface TaskState {
  taskId: string | null;
  progress: TaskProgress | null;
  uploading: boolean;
}

interface TaskActions {
  startUpload: (files: File[]) => Promise<void>;
  setProgress: (progress: TaskProgress | null) => void;
  close: () => void;
  reset: () => void;
}

interface WSMessage {
  type: "progress" | "completed" | "error";
  data: TaskProgress | Record<string, unknown>;
}

/** Module-level ref holding the active WebSocket so it can be cleaned up. */
let activeWs: WebSocket | null = null;

export const useTaskStore = create<TaskState & TaskActions>((set) => ({
  taskId: null,
  progress: null,
  uploading: false,

  startUpload: async (files: File[]) => {
    set({ uploading: true });
    try {
      const result = await filesApi.uploadFiles(files);
      const taskId = result.task_id;
      set({ taskId, uploading: false });

      // Close any previous connection
      if (activeWs) {
        activeWs.close();
        activeWs = null;
      }

      // Connect WebSocket to track progress
      const protocol =
        window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws/tasks/${taskId}`;
      const ws = new WebSocket(wsUrl);
      activeWs = ws;

      ws.addEventListener("message", (event: MessageEvent) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          if (msg.type === "progress") {
            set({ progress: msg.data as TaskProgress });
          } else if (msg.type === "completed") {
            set({
              progress: msg.data as TaskProgress,
            });
            ws.close();
            activeWs = null;
          } else if (msg.type === "error") {
            ws.close();
            activeWs = null;
          }
        } catch {
          // Ignore malformed messages
        }
      });
    } catch (err) {
      set({ uploading: false });
      throw err;
    }
  },

  setProgress: (progress) => set({ progress }),

  close: () => {
    if (activeWs) {
      activeWs.close();
      activeWs = null;
    }
  },

  reset: () => {
    if (activeWs) {
      activeWs.close();
      activeWs = null;
    }
    set({ taskId: null, progress: null, uploading: false });
  },
}));
