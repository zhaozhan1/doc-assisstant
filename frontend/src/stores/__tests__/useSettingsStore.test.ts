import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useSettingsStore } from "../useSettingsStore";
import * as settingsApi from "../../api/settings";
import type {
  KBSettings,
  LLMSettings,
  GenerationSettings,
  OnlineSearchConfig,
} from "../../types/api";

const mockKB: KBSettings = {
  source_folder: "/docs",
  db_path: "/db",
  chunk_size: 512,
  chunk_overlap: 50,
};

const mockLLM: LLMSettings = {
  default_provider: "ollama",
  ollama_base_url: "http://localhost:11434",
  ollama_chat_model: "qwen2.5",
  ollama_embed_model: "bge-large-zh-v1.5",
  claude_base_url: "",
  claude_api_key: "",
  claude_chat_model: "",
};

const mockGeneration: GenerationSettings = {
  output_format: "docx",
  save_path: "/output",
  include_sources: true,
  word_template_path: "",
};

const mockOnlineSearch: OnlineSearchConfig = {
  enabled: false,
  provider: "",
  api_key: "",
  base_url: "",
  domains: [],
  max_results: 10,
};

describe("useSettingsStore", () => {
  beforeEach(() => {
    useSettingsStore.setState({
      kb: null,
      llm: null,
      generation: null,
      onlineSearch: null,
      loading: false,
      error: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("fetchAllConfigs", () => {
    it("loads all configs", async () => {
      vi.spyOn(settingsApi, "getKBConfig").mockResolvedValue(mockKB);
      vi.spyOn(settingsApi, "getLLMConfig").mockResolvedValue(mockLLM);
      vi.spyOn(settingsApi, "getGenerationConfig").mockResolvedValue(
        mockGeneration,
      );
      vi.spyOn(settingsApi, "getOnlineSearchConfig").mockResolvedValue(
        mockOnlineSearch,
      );

      await useSettingsStore.getState().fetchAllConfigs();

      const state = useSettingsStore.getState();
      expect(state.kb).toEqual(mockKB);
      expect(state.llm).toEqual(mockLLM);
      expect(state.generation).toEqual(mockGeneration);
      expect(state.onlineSearch).toEqual(mockOnlineSearch);
      expect(state.loading).toBe(false);
    });

    it("handles error", async () => {
      vi.spyOn(settingsApi, "getKBConfig").mockRejectedValue(
        new Error("config fail"),
      );
      vi.spyOn(settingsApi, "getLLMConfig").mockResolvedValue(mockLLM);
      vi.spyOn(settingsApi, "getGenerationConfig").mockResolvedValue(
        mockGeneration,
      );
      vi.spyOn(settingsApi, "getOnlineSearchConfig").mockResolvedValue(
        mockOnlineSearch,
      );

      await useSettingsStore.getState().fetchAllConfigs();

      expect(useSettingsStore.getState().error).toBe("config fail");
    });
  });

  describe("updateKB", () => {
    it("updates KB config", async () => {
      const updated = { ...mockKB, chunk_size: 1024 };
      vi.spyOn(settingsApi, "updateKBConfig").mockResolvedValue(updated);

      await useSettingsStore.getState().updateKB({ chunk_size: 1024 });

      expect(useSettingsStore.getState().kb).toEqual(updated);
    });

    it("handles error", async () => {
      vi.spyOn(settingsApi, "updateKBConfig").mockRejectedValue(
        new Error("update fail"),
      );

      await useSettingsStore.getState().updateKB({ chunk_size: 1024 });

      expect(useSettingsStore.getState().error).toBe("update fail");
    });
  });

  describe("updateLLM", () => {
    it("updates LLM config", async () => {
      const updated = { ...mockLLM, default_provider: "claude" };
      vi.spyOn(settingsApi, "updateLLMConfig").mockResolvedValue(updated);

      await useSettingsStore
        .getState()
        .updateLLM({ default_provider: "claude" });

      expect(useSettingsStore.getState().llm).toEqual(updated);
    });
  });

  describe("updateGeneration", () => {
    it("updates generation config", async () => {
      const updated = { ...mockGeneration, output_format: "pdf" };
      vi.spyOn(settingsApi, "updateGenerationConfig").mockResolvedValue(
        updated,
      );

      await useSettingsStore
        .getState()
        .updateGeneration({ output_format: "pdf" });

      expect(useSettingsStore.getState().generation).toEqual(updated);
    });
  });

  describe("updateOnlineSearch", () => {
    it("updates online search config", async () => {
      const updated = { ...mockOnlineSearch, enabled: true };
      vi.spyOn(settingsApi, "updateOnlineSearchConfig").mockResolvedValue(
        updated,
      );

      await useSettingsStore
        .getState()
        .updateOnlineSearch({ enabled: true });

      expect(useSettingsStore.getState().onlineSearch).toEqual(updated);
    });
  });

  describe("testConnection", () => {
    it("returns test result", async () => {
      vi.spyOn(settingsApi, "testConnection").mockResolvedValue({
        success: true,
        message: "OK",
      });

      const result =
        await useSettingsStore.getState().testConnection({ api_key: "k" });

      expect(result).toEqual({ success: true, message: "OK" });
    });

    it("handles error", async () => {
      vi.spyOn(settingsApi, "testConnection").mockRejectedValue(
        new Error("test fail"),
      );

      const result =
        await useSettingsStore.getState().testConnection({ api_key: "k" });

      expect(result.success).toBe(false);
      expect(result.message).toContain("test fail");
    });
  });

  describe("browseDirectory", () => {
    it("returns browse result", async () => {
      const browseResult = {
        path: "/docs",
        children: [{ name: "a.docx", path: "/docs/a.docx", is_dir: false }],
      };
      vi.spyOn(settingsApi, "browseDirectory").mockResolvedValue(browseResult);

      const result =
        await useSettingsStore.getState().browseDirectory("/docs");

      expect(result).toEqual(browseResult);
    });
  });
});
