import client from "./client";
import type { SearchRequest, UnifiedSearchResult } from "../types/api";

export const search = async (
  request: SearchRequest,
): Promise<UnifiedSearchResult[]> => {
  const { data } = await client.post("/search", request);
  return data;
};

export const searchLocal = async (
  request: SearchRequest,
): Promise<UnifiedSearchResult[]> => {
  const { data } = await client.post("/search/local", request);
  return data;
};
