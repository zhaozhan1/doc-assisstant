import { create } from "zustand";
import type { IndexedFile, KBStats, FileListParams } from "../types/api";
import * as filesApi from "../api/files";
import * as statsApi from "../api/stats";

interface FileState {
  files: IndexedFile[];
  stats: KBStats | null;
  loading: boolean;
  error: string | null;
}

interface FileActions {
  fetchFiles: (params?: FileListParams) => Promise<void>;
  fetchStats: () => Promise<void>;
  deleteFile: (sourceFile: string) => Promise<void>;
  uploadFiles: (files: File[]) => Promise<string>;
}

export const useFileStore = create<FileState & FileActions>((set) => ({
  files: [],
  stats: null,
  loading: false,
  error: null,

  fetchFiles: async (params?: FileListParams) => {
    set({ loading: true, error: null });
    try {
      const files = await filesApi.listFiles(params);
      set({ files, loading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "加载文件列表失败",
        loading: false,
      });
    }
  },

  fetchStats: async () => {
    set({ error: null });
    try {
      const stats = await statsApi.getStats();
      set({ stats });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "加载统计失败",
      });
    }
  },

  deleteFile: async (sourceFile: string) => {
    set({ loading: true, error: null });
    try {
      await filesApi.deleteFile(sourceFile);
      const files = await filesApi.listFiles();
      set({ files, loading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "删除文件失败",
        loading: false,
      });
    }
  },

  uploadFiles: async (files: File[]) => {
    set({ loading: true, error: null });
    try {
      const result = await filesApi.uploadFiles(files);
      set({ loading: false });
      return result.task_id;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "上传失败";
      set({ error: msg, loading: false });
      throw err;
    }
  },
}));
