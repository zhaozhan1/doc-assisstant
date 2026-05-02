import { create } from "zustand";
import type {
  KBSettings,
  KBSettingsUpdate,
  LLMSettings,
  LLMSettingsUpdate,
  GenerationSettings,
  GenerationSettingsUpdate,
  OnlineSearchConfig,
  OnlineSearchConfigUpdate,
  ConnectionTestResult,
  BrowseResult,
} from "../types/api";
import * as settingsApi from "../api/settings";

interface SettingsState {
  kb: KBSettings | null;
  llm: LLMSettings | null;
  generation: GenerationSettings | null;
  onlineSearch: OnlineSearchConfig | null;
  loading: boolean;
  error: string | null;
}

interface SettingsActions {
  fetchAllConfigs: () => Promise<void>;
  updateKB: (update: KBSettingsUpdate) => Promise<void>;
  updateLLM: (update: LLMSettingsUpdate) => Promise<void>;
  updateGeneration: (update: GenerationSettingsUpdate) => Promise<void>;
  updateOnlineSearch: (update: OnlineSearchConfigUpdate) => Promise<void>;
  testConnection: (
    config: OnlineSearchConfigUpdate,
  ) => Promise<ConnectionTestResult>;
  browseDirectory: (path?: string) => Promise<BrowseResult>;
}

export const useSettingsStore = create<SettingsState & SettingsActions>(
  (set) => ({
    kb: null,
    llm: null,
    generation: null,
    onlineSearch: null,
    loading: false,
    error: null,

    fetchAllConfigs: async () => {
      set({ loading: true, error: null });
      try {
        const [kb, llm, generation, onlineSearch] = await Promise.all([
          settingsApi.getKBConfig(),
          settingsApi.getLLMConfig(),
          settingsApi.getGenerationConfig(),
          settingsApi.getOnlineSearchConfig(),
        ]);
        set({ kb, llm, generation, onlineSearch, loading: false });
      } catch (err) {
        set({
          error: err instanceof Error ? err.message : "加载配置失败",
          loading: false,
        });
      }
    },

    updateKB: async (update: KBSettingsUpdate) => {
      set({ error: null });
      try {
        const kb = await settingsApi.updateKBConfig(update);
        set({ kb });
      } catch (err) {
        set({
          error: err instanceof Error ? err.message : "更新知识库配置失败",
        });
      }
    },

    updateLLM: async (update: LLMSettingsUpdate) => {
      set({ error: null });
      try {
        const llm = await settingsApi.updateLLMConfig(update);
        set({ llm });
      } catch (err) {
        set({
          error: err instanceof Error ? err.message : "更新LLM配置失败",
        });
      }
    },

    updateGeneration: async (update: GenerationSettingsUpdate) => {
      set({ error: null });
      try {
        const generation = await settingsApi.updateGenerationConfig(update);
        set({ generation });
      } catch (err) {
        set({
          error: err instanceof Error ? err.message : "更新生成配置失败",
        });
      }
    },

    updateOnlineSearch: async (update: OnlineSearchConfigUpdate) => {
      set({ error: null });
      try {
        const onlineSearch =
          await settingsApi.updateOnlineSearchConfig(update);
        set({ onlineSearch });
      } catch (err) {
        set({
          error: err instanceof Error ? err.message : "更新在线搜索配置失败",
        });
      }
    },

    testConnection: async (config: OnlineSearchConfigUpdate) => {
      try {
        return await settingsApi.testConnection(config);
      } catch (err) {
        return {
          success: false,
          message: err instanceof Error ? err.message : "连接测试失败",
        };
      }
    },

    browseDirectory: async (path?: string) => {
      return await settingsApi.browseDirectory(path);
    },
  }),
);
