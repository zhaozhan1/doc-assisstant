import client from "./client";
import type { GenerationRequest, GenerationResult } from "../types/api";

export const generate = async (
  request: GenerationRequest,
): Promise<GenerationResult> => {
  const { data } = await client.post("/generation/generate", request);
  return data;
};

export const generateStream = (
  request: GenerationRequest,
): EventSource => {
  const params = new URLSearchParams();
  params.set("description", request.description);
  if (request.selected_refs) {
    params.set("selected_refs", JSON.stringify(request.selected_refs));
  }
  if (request.requirements) {
    params.set("requirements", request.requirements);
  }
  if (request.template_id) {
    params.set("template_id", request.template_id);
  }
  return new EventSource(
    `/api/generation/generate/stream?${params.toString()}`,
  );
};
