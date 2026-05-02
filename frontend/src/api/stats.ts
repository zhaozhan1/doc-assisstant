import client from "./client";
import type { KBStats } from "../types/api";

export const getStats = async (): Promise<KBStats> => {
  const { data } = await client.get("/stats");
  return data;
};
