import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSSE } from "../useSSE";
import type { GenerationRequest } from "../../types/api";

function createMockReader(chunks: string[]) {
  let index = 0;
  const encoder = new TextEncoder();
  const encoded = chunks.map((c) => encoder.encode(c));
  return {
    read: vi.fn(async () => {
      if (index < encoded.length) {
        return { done: false, value: encoded[index++] };
      }
      return { done: true, value: undefined };
    }),
    cancel: vi.fn(),
  };
}

function createMockBody(reader: ReturnType<typeof createMockReader>) {
  return {
    getReader: () => reader,
  };
}

function createMockResponse(body: ReturnType<typeof createMockBody>) {
  return {
    ok: true,
    body: body as unknown as ReadableStream<Uint8Array>,
    status: 200,
  };
}

describe("useSSE", () => {
  let mockFetch: vi.Mock;

  beforeEach(() => {
    mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useSSE());
    expect(result.current.content).toBe("");
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("accumulates content from SSE tokens", async () => {
    const reader = createMockReader([
      'data: {"token": "Hello"}\n\n',
      'data: {"token": " World"}\n\n',
      "data: [DONE]\n\n",
    ]);
    const body = createMockBody(reader);
    mockFetch.mockResolvedValue(createMockResponse(body));

    const { result } = renderHook(() => useSSE());

    const request: GenerationRequest = { description: "test" };

    await act(async () => {
      await result.current.start(request);
    });

    expect(result.current.content).toBe("Hello World");
    expect(result.current.isStreaming).toBe(false);
  });

  it("sets isStreaming during streaming", async () => {
    const encoder = new TextEncoder();
    let resolveBlock: () => void;
    const blockPromise = new Promise<void>((r) => {
      resolveBlock = r;
    });

    const controlledReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: encoder.encode('data: {"token": "Hi"}\n\n'),
        })
        .mockImplementationOnce(async () => {
          await blockPromise;
          return { done: true, value: undefined };
        }),
      cancel: vi.fn(),
    };

    const body = createMockBody(controlledReader);
    mockFetch.mockResolvedValue(createMockResponse(body));

    const { result } = renderHook(() => useSSE());

    // Start streaming but don't await — let it run
    let startPromise: Promise<void>;
    await act(async () => {
      startPromise = result.current.start({ description: "test" });
    });

    // The stream has processed the first chunk and is now waiting
    // but since we used act, the state should have updated
    expect(result.current.isStreaming).toBe(true);
    expect(result.current.content).toBe("Hi");

    // Release the block
    resolveBlock!();

    await act(async () => {
      await startPromise!;
    });

    expect(result.current.isStreaming).toBe(false);
  });

  it("handles fetch error", async () => {
    mockFetch.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      await result.current.start({ description: "test" });
    });

    expect(result.current.error).toBe("Network error");
    expect(result.current.isStreaming).toBe(false);
  });

  it("handles non-ok response", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      await result.current.start({ description: "test" });
    });

    expect(result.current.error).toContain("500");
    expect(result.current.isStreaming).toBe(false);
  });

  it("abort cancels the stream", async () => {
    let capturedSignal: AbortSignal | undefined;
    const encoder = new TextEncoder();

    let resolveBlock: () => void;
    const blockPromise = new Promise<void>((r) => {
      resolveBlock = r;
    });

    const controlledReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: encoder.encode('data: {"token": "X"}\n\n'),
        })
        .mockImplementationOnce(async () => {
          await blockPromise;
          return { done: true, value: undefined };
        }),
      cancel: vi.fn(),
    };

    mockFetch.mockImplementation(async (_url: string, opts: RequestInit) => {
      capturedSignal = opts.signal;
      return createMockResponse(createMockBody(controlledReader));
    });

    const { result } = renderHook(() => useSSE());

    let startPromise: Promise<void>;
    await act(async () => {
      startPromise = result.current.start({ description: "test" });
    });

    expect(capturedSignal).toBeDefined();
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      result.current.abort();
    });

    // Resolve the block so the stream can complete
    resolveBlock!();

    await act(async () => {
      await startPromise!;
    });

    expect(capturedSignal?.aborted).toBe(true);
  });

  it("calls POST to correct endpoint", async () => {
    const reader = createMockReader([]);
    const body = createMockBody(reader);
    mockFetch.mockResolvedValue(createMockResponse(body));

    const { result } = renderHook(() => useSSE());

    const request: GenerationRequest = {
      description: "write a report",
      selected_refs: ["ref1"],
    };

    await act(async () => {
      await result.current.start(request);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/generation/generate/stream",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify(request),
      }),
    );
  });

  it("resets content on new start call", async () => {
    // First stream
    const reader1 = createMockReader([
      'data: {"token": "First"}\n\n',
      "data: [DONE]\n\n",
    ]);
    const body1 = createMockBody(reader1);
    mockFetch.mockResolvedValueOnce(createMockResponse(body1));

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      await result.current.start({ description: "test1" });
    });

    expect(result.current.content).toBe("First");

    // Second stream
    const reader2 = createMockReader([
      'data: {"token": "Second"}\n\n',
      "data: [DONE]\n\n",
    ]);
    const body2 = createMockBody(reader2);
    mockFetch.mockResolvedValueOnce(createMockResponse(body2));

    await act(async () => {
      await result.current.start({ description: "test2" });
    });

    expect(result.current.content).toBe("Second");
  });
});
