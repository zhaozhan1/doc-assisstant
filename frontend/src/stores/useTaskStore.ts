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
  reset: () => void;
}

interface WSMessage {
  type: "progress" | "completed" | "error";
  data: TaskProgress | Record<string, unknown>;
}

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

      // Connect WebSocket to track progress
      const protocol =
        window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws/tasks/${taskId}`;
      const ws = new WebSocket(wsUrl);

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
          } else if (msg.type === "error") {
            ws.close();
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

  reset: () => set({ taskId: null, progress: null, uploading: false }),
}));
