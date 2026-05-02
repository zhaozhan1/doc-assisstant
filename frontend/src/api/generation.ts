import client from "./client";
import type { GenerationRequest, GenerationResult } from "../types/api";

export const generate = async (
  request: GenerationRequest,
): Promise<GenerationResult> => {
  const { data } = await client.post("/generation/generate", request);
  return data;
};
