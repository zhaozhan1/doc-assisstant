import client from "./client";
import type {
  GenerationRequest,
  GenerationResult,
  PptxRequest,
  PptxResult,
} from "../types/api";

export const generate = async (
  request: GenerationRequest,
): Promise<GenerationResult> => {
  const { data } = await client.post("/generation/generate", request);
  return data;
};

export const generatePptx = async (
  request: PptxRequest,
): Promise<{ task_id: string }> => {
  const { data } = await client.post("/generation/generate-pptx", request);
  return data;
};

export const getPptxResult = async (
  taskId: string,
): Promise<PptxResult> => {
  const { data } = await client.get(`/generation/pptx-result/${taskId}`);
  return data;
};
