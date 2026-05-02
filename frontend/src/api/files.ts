import client from "./client";
import type { IndexedFile, FileListParams } from "../types/api";

export const listFiles = async (
  params?: FileListParams,
): Promise<IndexedFile[]> => {
  const { data } = await client.get("/files", { params });
  return data;
};

export const uploadFiles = async (
  files: File[],
): Promise<{ task_id: string }> => {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  const { data } = await client.post("/files/upload", formData);
  return data;
};

export const deleteFile = async (
  sourceFile: string,
): Promise<{ status: string }> => {
  const { data } = await client.delete(`/files/${sourceFile}`);
  return data;
};

export const reindexFile = async (
  sourceFile: string,
): Promise<{ status: string; chunks_count: number }> => {
  const { data } = await client.post(`/files/${sourceFile}/reindex`);
  return data;
};

export const updateClassification = async (
  sourceFile: string,
  docType: string,
): Promise<{ status: string }> => {
  const { data } = await client.put(`/files/${sourceFile}/classification`, {
    doc_type: docType,
  });
  return data;
};

export const downloadFile = (filePath: string): string => {
  return `/api/files/download/${filePath}`;
};
