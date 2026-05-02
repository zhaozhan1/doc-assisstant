import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useWebSocket } from "../useWebSocket";
import type { TaskProgress } from "../../types/api";

function createMockWS() {
  const listeners: Record<string, EventListener[]> = {};
  const ws = {
    close: vi.fn(),
    send: vi.fn(),
    addEventListener: vi.fn((event: string, handler: EventListener) => {
      listeners[event] = listeners[event] || [];
      listeners[event].push(handler);
    }),
    removeEventListener: vi.fn(),
    readyState: WebSocket.OPEN,
    _listeners: listeners,
    _trigger(event: string, data: unknown) {
      const handlers = listeners[event] || [];
      const detail =
        typeof data === "string" ? { data } : { data: JSON.stringify(data) };
      const msgEvent = new MessageEvent("message", detail);
      for (const h of handlers) {
        h(msgEvent as Event);
      }
    },
    _open() {
      const handlers = listeners["open"] || [];
      for (const h of handlers) h(new Event("open"));
    },
    _error() {
      const handlers = listeners["error"] || [];
      for (const h of handlers) h(new Event("error"));
    },
    _close() {
      const handlers = listeners["close"] || [];
      for (const h of handlers) h(new CloseEvent("close"));
    },
  };
  return ws;
}

// Use a class-based mock so `new MockWS()` works
let mockWSInstance: ReturnType<typeof createMockWS>;

class MockWS {
  close: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  readyState: number;

  constructor(url: string | URL) {
    mockWSInstance = createMockWS();
    this.close = mockWSInstance.close;
    this.send = mockWSInstance.send;
    this.addEventListener = mockWSInstance.addEventListener;
    this.removeEventListener = mockWSInstance.removeEventListener;
    this.readyState = mockWSInstance.readyState;
    // Store url for assertions
    MockWS.lastUrl = url.toString();
  }

  static lastUrl: string = "";

  static get instance() {
    return mockWSInstance;
  }
}

describe("useWebSocket", () => {
  let OrigWS: typeof WebSocket;

  beforeEach(() => {
    OrigWS = globalThis.WebSocket;
    MockWS.lastUrl = "";
    mockWSInstance = undefined as unknown as ReturnType<typeof createMockWS>;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).WebSocket = MockWS;
  });

  afterEach(() => {
    globalThis.WebSocket = OrigWS;
    vi.restoreAllMocks();
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useWebSocket());
    expect(result.current.progress).toBeNull();
    expect(result.current.status).toBe("idle");
  });

  it("connects via WebSocket when connect is called", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });

    expect(MockWS.lastUrl).toContain("/ws/tasks/task-123");
  });

  it("updates status to connected on open", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });

    act(() => {
      MockWS.instance._open();
    });

    expect(result.current.status).toBe("connected");
  });

  it("updates progress on progress message", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });

    act(() => {
      MockWS.instance._open();
    });

    const progressData: TaskProgress = {
      task_id: "task-123",
      status: "running",
      total: 10,
      processed: 5,
      success: 4,
      failed: 1,
      skipped: 0,
      failed_files: [{ path: "a.docx", status: "failed", error: "bad" }],
      pending_files: [],
      created_at: "2026-01-01T00:00:00",
      updated_at: "2026-01-01T00:00:01",
    };

    act(() => {
      MockWS.instance._trigger("message", {
        type: "progress",
        data: progressData,
      });
    });

    expect(result.current.progress).toEqual(progressData);
    expect(result.current.status).toBe("connected");
  });

  it("updates status to completed on completed message", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });
    act(() => {
      MockWS.instance._open();
    });

    const progressData: TaskProgress = {
      task_id: "task-123",
      status: "completed",
      total: 10,
      processed: 10,
      success: 10,
      failed: 0,
      skipped: 0,
      failed_files: [],
      pending_files: [],
      created_at: "2026-01-01T00:00:00",
      updated_at: "2026-01-01T00:00:02",
    };

    act(() => {
      MockWS.instance._trigger("message", {
        type: "completed",
        data: progressData,
      });
    });

    expect(result.current.status).toBe("completed");
    expect(result.current.progress).toEqual(progressData);
  });

  it("updates status to error on error message", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });
    act(() => {
      MockWS.instance._open();
    });

    act(() => {
      MockWS.instance._trigger("message", {
        type: "error",
        data: { detail: "Something went wrong" },
      });
    });

    expect(result.current.status).toBe("error");
  });

  it("sends cancel command", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });
    act(() => {
      MockWS.instance._open();
    });

    act(() => {
      result.current.cancel();
    });

    expect(MockWS.instance.send).toHaveBeenCalledWith(
      JSON.stringify({ type: "cancel" }),
    );
  });

  it("closes WebSocket on unmount", () => {
    const { result, unmount } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });

    unmount();

    expect(MockWS.instance.close).toHaveBeenCalled();
  });

  it("handles WebSocket error event", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-123");
    });
    act(() => {
      MockWS.instance._open();
    });

    act(() => {
      MockWS.instance._error();
    });

    expect(result.current.status).toBe("error");
  });

  it("closes previous connection on new connect", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect("task-1");
    });
    const firstWS = mockWSInstance;

    act(() => {
      result.current.connect("task-2");
    });

    expect(firstWS.close).toHaveBeenCalled();
    expect(MockWS.lastUrl).toContain("/ws/tasks/task-2");
  });
});
