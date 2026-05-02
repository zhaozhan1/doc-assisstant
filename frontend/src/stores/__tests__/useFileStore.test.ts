import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useFileStore } from "../useFileStore";
import * as filesApi from "../../api/files";
import * as statsApi from "../../api/stats";
import type { IndexedFile, KBStats } from "../../types/api";

describe("useFileStore", () => {
  beforeEach(() => {
    useFileStore.setState({
      files: [],
      stats: null,
      loading: false,
      error: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("fetchFiles", () => {
    it("loads files from API", async () => {
      const mockFiles: IndexedFile[] = [
        {
          source_file: "a.docx",
          file_name: "a.docx",
          doc_type: "通知",
          doc_date: "2026-01-01",
          file_md5: "abc",
          chunk_count: 5,
          duplicate_with: null,
        },
      ];
      vi.spyOn(filesApi, "listFiles").mockResolvedValue(mockFiles);

      await useFileStore.getState().fetchFiles();

      const state = useFileStore.getState();
      expect(state.files).toEqual(mockFiles);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("passes params to API", async () => {
      const spy = vi.spyOn(filesApi, "listFiles").mockResolvedValue([]);

      await useFileStore.getState().fetchFiles({ doc_types: "通知" });

      expect(spy).toHaveBeenCalledWith({ doc_types: "通知" });
    });

    it("handles error", async () => {
      vi.spyOn(filesApi, "listFiles").mockRejectedValue(new Error("fail"));

      await useFileStore.getState().fetchFiles();

      const state = useFileStore.getState();
      expect(state.error).toBe("fail");
      expect(state.loading).toBe(false);
    });
  });

  describe("fetchStats", () => {
    it("loads stats from API", async () => {
      const mockStats: KBStats = {
        total_files: 10,
        type_distribution: { 通知: 5, 报告: 5 },
        last_updated: "2026-01-01",
      };
      vi.spyOn(statsApi, "getStats").mockResolvedValue(mockStats);

      await useFileStore.getState().fetchStats();

      expect(useFileStore.getState().stats).toEqual(mockStats);
    });

    it("handles error", async () => {
      vi.spyOn(statsApi, "getStats").mockRejectedValue(new Error("stats fail"));

      await useFileStore.getState().fetchStats();

      expect(useFileStore.getState().error).toBe("stats fail");
    });
  });

  describe("deleteFile", () => {
    it("deletes and refreshes file list", async () => {
      vi.spyOn(filesApi, "deleteFile").mockResolvedValue({ status: "ok" });
      vi.spyOn(filesApi, "listFiles").mockResolvedValue([]);

      await useFileStore.getState().deleteFile("a.docx");

      expect(filesApi.deleteFile).toHaveBeenCalledWith("a.docx");
      expect(filesApi.listFiles).toHaveBeenCalled();
    });

    it("handles error", async () => {
      vi.spyOn(filesApi, "deleteFile").mockRejectedValue(
        new Error("delete fail"),
      );

      await useFileStore.getState().deleteFile("a.docx");

      expect(useFileStore.getState().error).toBe("delete fail");
    });
  });

  describe("uploadFiles", () => {
    it("uploads files and returns task_id", async () => {
      const file = new File(["content"], "test.docx");
      vi.spyOn(filesApi, "uploadFiles").mockResolvedValue({
        task_id: "task-1",
      });

      const taskId = await useFileStore.getState().uploadFiles([file]);

      expect(taskId).toBe("task-1");
      expect(filesApi.uploadFiles).toHaveBeenCalledWith([file]);
    });

    it("handles error", async () => {
      vi.spyOn(filesApi, "uploadFiles").mockRejectedValue(
        new Error("upload fail"),
      );

      await expect(
        useFileStore.getState().uploadFiles([]),
      ).rejects.toThrow("upload fail");
    });
  });
});
