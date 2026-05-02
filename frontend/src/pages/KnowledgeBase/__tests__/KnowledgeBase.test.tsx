import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import KnowledgeBase from "../index";
import type { IndexedFile, KBStats } from "../../../types/api";

// ---- Mock data ----
const mockStats: KBStats = {
  total_files: 128,
  type_distribution: { 通知: 35, 报告: 28, 方案: 22, 其他: 43 },
  last_updated: "2026-05-01T14:32:00",
};

const mockFiles: IndexedFile[] = [
  {
    source_file: "notice1.docx",
    file_name: "关于开展年度检查的通知.docx",
    doc_type: "通知",
    doc_date: "2026-04-15",
    file_md5: "abc123",
    chunk_count: 8,
    duplicate_with: null,
  },
  {
    source_file: "report1.docx",
    file_name: "2026年第一季度工作报告.docx",
    doc_type: "报告",
    doc_date: "2026-03-31",
    file_md5: "def456",
    chunk_count: 12,
    duplicate_with: null,
  },
  {
    source_file: "plan1.docx",
    file_name: "2026年信息化建设方案.docx",
    doc_type: "方案",
    doc_date: "2026-02-20",
    file_md5: "ghi789",
    chunk_count: 15,
    duplicate_with: null,
  },
];

// ---- Store mock state (mutable for test overrides) ----
let mockFileStoreState: Record<string, unknown>;
let mockTaskStoreState: Record<string, unknown>;

const mockFetchFiles = vi.fn().mockResolvedValue(undefined);
const mockFetchStats = vi.fn().mockResolvedValue(undefined);
const mockDeleteFile = vi.fn().mockResolvedValue(undefined);
const mockStartUpload = vi.fn().mockResolvedValue(undefined);
const mockReset = vi.fn();

function resetMockState() {
  mockFileStoreState = {
    files: mockFiles,
    stats: mockStats,
    loading: false,
    error: null,
    fetchFiles: mockFetchFiles,
    fetchStats: mockFetchStats,
    deleteFile: mockDeleteFile,
    uploadFiles: vi.fn(),
  };
  mockTaskStoreState = {
    taskId: null,
    progress: null,
    uploading: false,
    startUpload: mockStartUpload,
    setProgress: vi.fn(),
    close: vi.fn(),
    reset: mockReset,
  };
}

vi.mock("../../../stores/useFileStore", () => ({
  useFileStore: Object.assign(
    (selector?: (state: Record<string, unknown>) => unknown) =>
      selector ? selector(mockFileStoreState) : mockFileStoreState,
    { getState: vi.fn(), setState: vi.fn(), subscribe: vi.fn() },
  ),
}));

vi.mock("../../../stores/useTaskStore", () => ({
  useTaskStore: Object.assign(
    (selector?: (state: Record<string, unknown>) => unknown) =>
      selector ? selector(mockTaskStoreState) : mockTaskStoreState,
    { getState: vi.fn(), setState: vi.fn(), subscribe: vi.fn() },
  ),
}));

vi.mock("../../../api/files", () => ({
  listFiles: vi.fn().mockResolvedValue([]),
  uploadFiles: vi.fn().mockResolvedValue({ task_id: "test-task" }),
  deleteFile: vi.fn().mockResolvedValue({ status: "ok" }),
  reindexFile: vi.fn().mockResolvedValue({ status: "ok", chunks_count: 5 }),
  updateClassification: vi
    .fn()
    .mockResolvedValue({ status: "ok" }),
  downloadFile: (p: string) => `/api/files/download/${p}`,
}));

describe("KnowledgeBase", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetMockState();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls fetchFiles and fetchStats on mount", () => {
    render(<KnowledgeBase />);
    expect(mockFetchFiles).toHaveBeenCalledOnce();
    expect(mockFetchStats).toHaveBeenCalledOnce();
  });

  it("renders stats cards with data from store", () => {
    render(<KnowledgeBase />);

    // Total files
    expect(screen.getByText("128")).toBeInTheDocument();

    // Type distribution tags
    expect(screen.getByText("通知 35")).toBeInTheDocument();
    expect(screen.getByText("报告 28")).toBeInTheDocument();
    expect(screen.getByText("方案 22")).toBeInTheDocument();
    expect(screen.getByText("其他 43")).toBeInTheDocument();

    // Last updated date shown
    expect(screen.getByText(/2026-05-01/)).toBeInTheDocument();
  });

  it("renders upload dragger area", () => {
    render(<KnowledgeBase />);
    expect(
      screen.getByText("拖拽文件到此处，或点击选择文件"),
    ).toBeInTheDocument();
  });

  it("renders filter bar with type select and sort", () => {
    render(<KnowledgeBase />);

    // Type label and default value are separate elements
    expect(screen.getByText("类型：")).toBeInTheDocument();
    expect(screen.getByText("全部")).toBeInTheDocument();
    // Sort select shows its default label
    expect(screen.getByText("最近更新")).toBeInTheDocument();
  });

  it("renders file table with correct columns and data", () => {
    render(<KnowledgeBase />);

    // Column headers
    expect(screen.getByText("文件名")).toBeInTheDocument();
    expect(screen.getByText("类型")).toBeInTheDocument();
    expect(screen.getByText("日期")).toBeInTheDocument();
    expect(screen.getByText("分块数")).toBeInTheDocument();
    expect(screen.getByText("操作")).toBeInTheDocument();

    // File data
    expect(
      screen.getByText("关于开展年度检查的通知.docx"),
    ).toBeInTheDocument();
    expect(screen.getByText("2026年第一季度工作报告.docx")).toBeInTheDocument();
  });

  it("handles delete with confirmation", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBase />);

    const deleteButtons = screen.getAllByText("删除");
    await user.click(deleteButtons[0]);

    // Popconfirm shows
    expect(screen.getByText("确定删除该文件吗？")).toBeInTheDocument();

    // Confirm
    await user.click(screen.getByText("确 定"));
    expect(mockDeleteFile).toHaveBeenCalledOnce();
  });

  it("handles reindex with confirmation", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBase />);

    const reindexButtons = screen.getAllByText("重新索引");
    await user.click(reindexButtons[0]);

    expect(screen.getByText("确定重新索引该文件吗？")).toBeInTheDocument();

    await user.click(screen.getByText("确 定"));
  });

  it("shows import progress when task is running", () => {
    mockTaskStoreState.taskId = "task-running";
    mockTaskStoreState.progress = {
      task_id: "task-running",
      status: "running",
      total: 50,
      processed: 20,
      success: 18,
      failed: 1,
      skipped: 1,
      failed_files: [],
      pending_files: [],
      created_at: "2026-05-01T10:00:00",
      updated_at: "2026-05-01T10:01:00",
    };

    render(<KnowledgeBase />);
    expect(screen.getByText("正在导入...")).toBeInTheDocument();
  });

  it("shows import result summary when task completed", () => {
    mockTaskStoreState.taskId = "task-done";
    mockTaskStoreState.progress = {
      task_id: "task-done",
      status: "completed",
      total: 10,
      processed: 10,
      success: 8,
      failed: 1,
      skipped: 1,
      failed_files: [],
      pending_files: [],
      created_at: "2026-05-01T10:00:00",
      updated_at: "2026-05-01T10:05:00",
    };

    render(<KnowledgeBase />);
    expect(screen.getByText("导入完成")).toBeInTheDocument();
  });
});
