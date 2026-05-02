import client from "./client";
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

export const getKBConfig = async (): Promise<KBSettings> => {
  const { data } = await client.get("/settings/knowledge-base");
  return data;
};

export const updateKBConfig = async (
  update: KBSettingsUpdate,
): Promise<KBSettings> => {
  const { data } = await client.put("/settings/knowledge-base", update);
  return data;
};

export const getLLMConfig = async (): Promise<LLMSettings> => {
  const { data } = await client.get("/settings/llm");
  return data;
};

export const updateLLMConfig = async (
  update: LLMSettingsUpdate,
): Promise<LLMSettings> => {
  const { data } = await client.put("/settings/llm", update);
  return data;
};

export const getGenerationConfig = async (): Promise<GenerationSettings> => {
  const { data } = await client.get("/settings/generation");
  return data;
};

export const updateGenerationConfig = async (
  update: GenerationSettingsUpdate,
): Promise<GenerationSettings> => {
  const { data } = await client.put("/settings/generation", update);
  return data;
};

export const getOnlineSearchConfig = async (): Promise<OnlineSearchConfig> => {
  const { data } = await client.get("/settings/online-search");
  return data;
};

export const updateOnlineSearchConfig = async (
  update: OnlineSearchConfigUpdate,
): Promise<OnlineSearchConfig> => {
  const { data } = await client.put("/settings/online-search", update);
  return data;
};

export const testConnection = async (
  config: OnlineSearchConfigUpdate,
): Promise<ConnectionTestResult> => {
  const { data } = await client.post("/settings/online-search/test-connection", config);
  return data;
};

export const browseDirectory = async (
  path: string = ".",
): Promise<BrowseResult> => {
  const { data } = await client.get("/settings/files/browse", {
    params: { path },
  });
  return data;
};
