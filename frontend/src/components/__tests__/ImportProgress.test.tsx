import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ImportProgress } from "../ImportProgress";
import type { TaskProgress } from "../../types/api";

const runningProgress: TaskProgress = {
  task_id: "task-1",
  status: "running",
  total: 100,
  processed: 45,
  success: 42,
  failed: 2,
  skipped: 1,
  failed_files: [],
  pending_files: [],
  created_at: "2026-05-01T10:00:00",
  updated_at: "2026-05-01T10:01:00",
};

const completedProgress: TaskProgress = {
  task_id: "task-1",
  status: "completed",
  total: 100,
  processed: 100,
  success: 95,
  failed: 3,
  skipped: 2,
  failed_files: [
    { path: "bad1.docx", status: "failed", error: "无法解析文件" },
    { path: "bad2.pdf", status: "failed", error: "文件损坏" },
    { path: "bad3.docx", status: "failed", error: "格式不支持" },
  ],
  pending_files: [],
  created_at: "2026-05-01T10:00:00",
  updated_at: "2026-05-01T10:05:00",
};

describe("ImportProgress", () => {
  describe("during import (status=running)", () => {
    it("renders progress bar with percentage", () => {
      render(
        <ImportProgress
          progress={runningProgress}
          onCancel={vi.fn()}
          onClose={vi.fn()}
        />,
      );

      expect(screen.getByText("正在导入...")).toBeInTheDocument();
      // 45% = 45/100
      expect(screen.getByText("45%")).toBeInTheDocument();
    });

    it("shows success/failed/skipped counts", () => {
      render(
        <ImportProgress
          progress={runningProgress}
          onCancel={vi.fn()}
          onClose={vi.fn()}
        />,
      );

      expect(screen.getByText("42")).toBeInTheDocument(); // success
      expect(screen.getByText("2")).toBeInTheDocument(); // failed
      expect(screen.getByText("1")).toBeInTheDocument(); // skipped
    });

    it("calls cancel when cancel button clicked", async () => {
      const user = userEvent.setup();
      const onCancel = vi.fn();

      render(
        <ImportProgress
          progress={runningProgress}
          onCancel={onCancel}
          onClose={vi.fn()}
        />,
      );

      await user.click(screen.getByRole("button", { name: /取\s*消/ }));
      expect(onCancel).toHaveBeenCalledOnce();
    });
  });

  describe("after import (status=completed)", () => {
    it("renders result summary with total count", () => {
      render(
        <ImportProgress
          progress={completedProgress}
          onCancel={vi.fn()}
          onClose={vi.fn()}
        />,
      );

      expect(screen.getByText("导入完成")).toBeInTheDocument();
      expect(screen.getByText(/100/)).toBeInTheDocument();
    });

    it("shows success/failed/skipped counts in result", () => {
      render(
        <ImportProgress
          progress={completedProgress}
          onCancel={vi.fn()}
          onClose={vi.fn()}
        />,
      );

      expect(screen.getByText("95")).toBeInTheDocument(); // success
      expect(screen.getByText("3")).toBeInTheDocument(); // failed
      expect(screen.getByText("2")).toBeInTheDocument(); // skipped
    });

    it("expands failure details on click", async () => {
      const user = userEvent.setup();
      render(
        <ImportProgress
          progress={completedProgress}
          onCancel={vi.fn()}
          onClose={vi.fn()}
        />,
      );

      // Initially failure details are not visible
      expect(screen.queryByText("bad1.docx")).not.toBeInTheDocument();

      // Click to expand
      await user.click(screen.getByText(/查看失败文件详情/));

      expect(screen.getByText("bad1.docx")).toBeInTheDocument();
      expect(screen.getByText("bad2.pdf")).toBeInTheDocument();
      expect(screen.getByText("bad3.docx")).toBeInTheDocument();
      expect(screen.getByText("无法解析文件")).toBeInTheDocument();
    });

    it("calls close when close button clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(
        <ImportProgress
          progress={completedProgress}
          onCancel={vi.fn()}
          onClose={onClose}
        />,
      );

      await user.click(screen.getByRole("button", { name: /关\s*闭/ }));
      expect(onClose).toHaveBeenCalledOnce();
    });
  });
});
