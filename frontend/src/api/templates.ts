import client from "./client";
import type { TemplateDef } from "../types/api";

export const listTemplates = async (
  docType?: string | null,
): Promise<TemplateDef[]> => {
  const { data } = await client.get("/templates", {
    params: docType ? { doc_type: docType } : undefined,
  });
  return data;
};

export const getTemplate = async (
  templateId: string,
): Promise<TemplateDef> => {
  const { data } = await client.get(`/templates/${templateId}`);
  return data;
};

export const createTemplate = async (
  template: TemplateDef,
): Promise<TemplateDef> => {
  const { data } = await client.post("/templates", template);
  return data;
};

export const updateTemplate = async (
  templateId: string,
  template: TemplateDef,
): Promise<TemplateDef> => {
  const { data } = await client.put(`/templates/${templateId}`, template);
  return data;
};

export const deleteTemplate = async (
  templateId: string,
): Promise<void> => {
  await client.delete(`/templates/${templateId}`);
};
