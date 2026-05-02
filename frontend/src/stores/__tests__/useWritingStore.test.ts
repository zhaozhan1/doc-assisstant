import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useWritingStore } from "../useWritingStore";
import * as generationApi from "../../api/generation";

describe("useWritingStore", () => {
  beforeEach(() => {
    useWritingStore.setState({
      mode: "onestep",
      content: "",
      isStreaming: false,
      error: null,
      selectedRefs: [],
      searchResults: [],
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts with default state", () => {
    const state = useWritingStore.getState();
    expect(state.mode).toBe("onestep");
    expect(state.content).toBe("");
    expect(state.isStreaming).toBe(false);
    expect(state.error).toBeNull();
    expect(state.selectedRefs).toEqual([]);
    expect(state.searchResults).toEqual([]);
  });

  describe("generate", () => {
    it("calls API and sets content", async () => {
      vi.spyOn(generationApi, "generate").mockResolvedValue({
        content: "生成的公文内容",
        sources: [],
        output_path: null,
        template_used: "default",
      });

      await useWritingStore.getState().generate({ description: "test" });

      const state = useWritingStore.getState();
      expect(state.content).toBe("生成的公文内容");
      expect(state.isStreaming).toBe(false);
      expect(state.error).toBeNull();
    });

    it("handles error", async () => {
      vi.spyOn(generationApi, "generate").mockRejectedValue(
        new Error("gen error"),
      );

      await useWritingStore.getState().generate({ description: "test" });

      const state = useWritingStore.getState();
      expect(state.error).toBe("gen error");
      expect(state.isStreaming).toBe(false);
    });

    it("sets loading state during generation", async () => {
      let resolveGen: () => void;
      const genPromise = new Promise<{
        content: string;
        sources: never[];
        output_path: null;
        template_used: string;
      }>((resolve) => {
        resolveGen = () =>
          resolve({
            content: "done",
            sources: [],
            output_path: null,
            template_used: "default",
          });
      });
      vi.spyOn(generationApi, "generate").mockReturnValue(genPromise);

      const promise = useWritingStore
        .getState()
        .generate({ description: "test" });

      expect(useWritingStore.getState().isStreaming).toBe(true);

      resolveGen!();
      await promise;

      expect(useWritingStore.getState().isStreaming).toBe(false);
    });
  });

  describe("startStream", () => {
    it("updates content as tokens arrive", async () => {
      const encoder = new TextEncoder();
      const reader = {
        read: vi
          .fn()
          .mockResolvedValueOnce({
            done: false,
            value: encoder.encode('data: {"token": "Hello"}\n\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: encoder.encode('data: {"token": " World"}\n\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: encoder.encode("data: [DONE]\n\n"),
          })
          .mockResolvedValue({ done: true, value: undefined }),
        cancel: vi.fn(),
      };

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          body: { getReader: () => reader },
        }),
      );

      await useWritingStore.getState().startStream({ description: "test" });

      const state = useWritingStore.getState();
      expect(state.content).toBe("Hello World");
      expect(state.isStreaming).toBe(false);
    });

    it("handles fetch error", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockRejectedValue(new Error("stream error")),
      );

      await useWritingStore.getState().startStream({ description: "test" });

      const state = useWritingStore.getState();
      expect(state.error).toBe("stream error");
      expect(state.isStreaming).toBe(false);
    });
  });

  describe("abortStream", () => {
    it("aborts active stream", async () => {
      const encoder = new TextEncoder();
      let resolveBlock: () => void;
      const blockPromise = new Promise<void>((r) => {
        resolveBlock = r;
      });

      const reader = {
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

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          body: { getReader: () => reader },
        }),
      );

      const promise = useWritingStore
        .getState()
        .startStream({ description: "test" });

      expect(useWritingStore.getState().isStreaming).toBe(true);

      useWritingStore.getState().abortStream();
      resolveBlock!();
      await promise;

      expect(useWritingStore.getState().isStreaming).toBe(false);
    });
  });

  it("setSelectedRefs updates refs", () => {
    useWritingStore.getState().setSelectedRefs(["ref1", "ref2"]);
    expect(useWritingStore.getState().selectedRefs).toEqual(["ref1", "ref2"]);
  });

  it("setSearchResults updates results", () => {
    const results = [
      {
        source_type: "local" as const,
        title: "test",
        content: "content",
        score: 0.9,
        metadata: {},
      },
    ];
    useWritingStore.getState().setSearchResults(results);
    expect(useWritingStore.getState().searchResults).toEqual(results);
  });

  it("setMode updates mode", () => {
    useWritingStore.getState().setMode("stepbystep");
    expect(useWritingStore.getState().mode).toBe("stepbystep");
  });
});
