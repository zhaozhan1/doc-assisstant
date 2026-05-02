import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useTaskStore } from "../useTaskStore";
import * as filesApi from "../../api/files";

// Mock WebSocket
class MockWS {
  close = vi.fn();
  send = vi.fn();
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  readyState = 1; // OPEN

  static lastUrl = "";
  constructor(url: string) {
    MockWS.lastUrl = url;
  }
}

describe("useTaskStore", () => {
  let OrigWS: typeof WebSocket;

  beforeEach(() => {
    OrigWS = globalThis.WebSocket;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).WebSocket = MockWS;
    useTaskStore.setState({
      taskId: null,
      progress: null,
      uploading: false,
    });
    MockWS.lastUrl = "";
  });

  afterEach(() => {
    globalThis.WebSocket = OrigWS;
    vi.restoreAllMocks();
  });

  it("starts in idle state", () => {
    const state = useTaskStore.getState();
    expect(state.taskId).toBeNull();
    expect(state.progress).toBeNull();
    expect(state.uploading).toBe(false);
  });

  it("startUpload uploads files and tracks task", async () => {
    const file = new File(["content"], "test.docx");
    vi.spyOn(filesApi, "uploadFiles").mockResolvedValue({
      task_id: "task-abc",
    });

    await useTaskStore.getState().startUpload([file]);

    const state = useTaskStore.getState();
    expect(state.taskId).toBe("task-abc");
    expect(state.uploading).toBe(false);
    expect(MockWS.lastUrl).toContain("/ws/tasks/task-abc");
    expect(filesApi.uploadFiles).toHaveBeenCalledWith([file]);
  });

  it("sets uploading while upload in progress", async () => {
    let resolveUpload: () => void;
    const uploadPromise = new Promise<{ task_id: string }>((resolve) => {
      resolveUpload = () => resolve({ task_id: "task-x" });
    });
    vi.spyOn(filesApi, "uploadFiles").mockReturnValue(uploadPromise);

    const promise = useTaskStore.getState().startUpload([]);

    // uploading should be true while awaiting
    expect(useTaskStore.getState().uploading).toBe(true);

    resolveUpload!();
    await promise;

    expect(useTaskStore.getState().uploading).toBe(false);
  });

  it("handles upload error", async () => {
    vi.spyOn(filesApi, "uploadFiles").mockRejectedValue(
      new Error("upload error"),
    );

    await expect(
      useTaskStore.getState().startUpload([]),
    ).rejects.toThrow("upload error");

    const state = useTaskStore.getState();
    expect(state.uploading).toBe(false);
    expect(state.taskId).toBeNull();
  });

  it("reset clears state", async () => {
    vi.spyOn(filesApi, "uploadFiles").mockResolvedValue({
      task_id: "task-1",
    });

    await useTaskStore.getState().startUpload([]);

    useTaskStore.getState().reset();

    const state = useTaskStore.getState();
    expect(state.taskId).toBeNull();
    expect(state.progress).toBeNull();
    expect(state.uploading).toBe(false);
  });
});
