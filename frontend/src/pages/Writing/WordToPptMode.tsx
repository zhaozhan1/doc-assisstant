import { useState, useEffect, useCallback } from "react";
import {
  Button,
  Tabs,
  Typography,
  Upload,
  Input,
  List,
  Alert,
  Spin,
  message,
} from "antd";
import {
  InboxOutlined,
  FileTextOutlined,
  SearchOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { useWritingStore } from "../../stores/useWritingStore";
import { listFiles, uploadFiles } from "../../api/files";
import type { IndexedFile, PptxRequest } from "../../types/api";
import SlideThumbnail from "./components/SlideThumbnail";
import GenerationSteps from "./components/GenerationSteps";

const { Dragger } = Upload;

interface SelectedFile {
  name: string;
  path: string;
}

type SourceTab = "upload" | "kb" | "session";

export function WordToPptMode() {
  const [activeTab, setActiveTab] = useState<SourceTab>("kb");
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [uploadingFile, setUploadingFile] = useState<File | null>(null);

  // KB tab state
  const [kbFiles, setKbFiles] = useState<IndexedFile[]>([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbSearch, setKbSearch] = useState("");

  // PPT generation state from store
  const isGeneratingPptx = useWritingStore((s) => s.isGeneratingPptx);
  const pptxResult = useWritingStore((s) => s.pptxResult);
  const pptxError = useWritingStore((s) => s.pptxError);
  const startPptxGeneration = useWritingStore((s) => s.startPptxGeneration);
  const resetPptxState = useWritingStore((s) => s.resetPptxState);
  const sessionGeneratedDocs = useWritingStore(
    (s) => s.sessionGeneratedDocs,
  );

  // Load KB files
  const fetchKbFiles = useCallback(async () => {
    setKbLoading(true);
    try {
      const files = await listFiles();
      setKbFiles(files.filter((f) => f.source_file.endsWith(".docx")));
    } catch {
      /* ignore */
    } finally {
      setKbLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "kb") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void fetchKbFiles();
    }
  }, [activeTab, fetchKbFiles]);

  // Reset generation state on mount
  useEffect(() => {
    resetPptxState();
  }, [resetPptxState]);

  const handleGenerate = useCallback(async () => {
    if (!selectedFile) {
      message.warning("请先选择文件");
      return;
    }

    let filePath = selectedFile.path;

    // For upload tab: upload file first, then find it in KB
    if (activeTab === "upload" && uploadingFile) {
      try {
        message.loading({ content: "正在上传文件...", key: "pptx-upload" });
        await uploadFiles([uploadingFile]);
        // Refresh KB and find the uploaded file
        const files = await listFiles();
        const docxFiles = files.filter((f) =>
          f.source_file.endsWith(".docx"),
        );
        const matched = docxFiles.find(
          (f) => f.file_name === uploadingFile.name,
        );
        if (!matched) {
          message.error({
            content: "文件上传后未在知识库中找到，请稍后重试",
            key: "pptx-upload",
          });
          return;
        }
        filePath = matched.source_file;
        message.success({ content: "文件上传成功", key: "pptx-upload" });
      } catch (err) {
        message.error({
          content: err instanceof Error ? err.message : "文件上传失败",
          key: "pptx-upload",
        });
        return;
      }
    }

    const request: PptxRequest = {
      source_type: activeTab,
      file_path: filePath,
    };

    startPptxGeneration(request);
  }, [
    selectedFile,
    activeTab,
    uploadingFile,
    startPptxGeneration,
  ]);

  // Determine step index from result
  const stepIndex = pptxResult?.step_index ?? 0;
  const totalSteps = pptxResult?.total_steps ?? 4;
  const isCompleted =
    pptxResult?.status === "completed" && pptxResult.output_path;
  const isFailed = !!pptxError;

  // Filter KB files by search
  const filteredKbFiles = kbSearch
    ? kbFiles.filter(
        (f) =>
          f.file_name.toLowerCase().includes(kbSearch.toLowerCase()) ||
          f.source_file.toLowerCase().includes(kbSearch.toLowerCase()),
      )
    : kbFiles;

  const canGenerate = selectedFile !== null && !isGeneratingPptx;

  return (
    <div style={{ display: "flex", gap: 16, height: "100%" }}>
      {/* Left panel - Source selection */}
      <div
        className="writing-panel"
        style={{
          flex: 1,
          background: "#fff",
          borderRadius: 8,
          padding: 24,
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Typography.Title
          level={5}
          style={{ marginTop: 0, marginBottom: 16 }}
        >
          选择 Word 文档
        </Typography.Title>

        <Tabs
          activeKey={activeTab}
          onChange={(key) => {
            setActiveTab(key as SourceTab);
            setSelectedFile(null);
            setUploadingFile(null);
          }}
          items={[
            {
              key: "upload",
              label: "上传文件",
              children: (
                <div>
                  <Dragger
                    accept=".docx"
                    beforeUpload={(file) => {
                      if (
                        !file.name.endsWith(".docx")
                      ) {
                        message.error("仅支持 .docx 格式文件");
                        return Upload.LIST_IGNORE;
                      }
                      setUploadingFile(file);
                      setSelectedFile({
                        name: file.name,
                        path: file.name,
                      });
                      return false;
                    }}
                    showUploadList={!!uploadingFile}
                    fileList={
                      uploadingFile
                        ? [
                            {
                              uid: "-1",
                              name: uploadingFile.name,
                              status: "done",
                            },
                          ]
                        : []
                    }
                    onRemove={() => {
                      setUploadingFile(null);
                      setSelectedFile(null);
                    }}
                  >
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">
                      点击或拖拽 .docx 文件到此处
                    </p>
                  </Dragger>
                  {uploadingFile && (
                    <Typography.Text
                      type="secondary"
                      style={{ fontSize: 12, marginTop: 8, display: "block" }}
                    >
                      文件将上传至知识库后进行转换
                    </Typography.Text>
                  )}
                </div>
              ),
            },
            {
              key: "kb",
              label: "知识库选择",
              children: (
                <div>
                  <Input
                    placeholder="搜索知识库中的文档..."
                    prefix={<SearchOutlined />}
                    value={kbSearch}
                    onChange={(e) => setKbSearch(e.target.value)}
                    style={{ marginBottom: 12 }}
                    allowClear
                  />
                  {kbLoading ? (
                    <div style={{ textAlign: "center", padding: 24 }}>
                      <Spin />
                    </div>
                  ) : filteredKbFiles.length === 0 ? (
                    <Typography.Text type="secondary">
                      {kbSearch ? "未找到匹配文档" : "暂无可选文档"}
                    </Typography.Text>
                  ) : (
                    <List
                      size="small"
                      dataSource={filteredKbFiles}
                      style={{ maxHeight: 320, overflow: "auto" }}
                      renderItem={(file) => (
                        <List.Item
                          style={{
                            cursor: "pointer",
                            padding: "8px 12px",
                            background:
                              selectedFile?.path === file.source_file
                                ? "#e6f7ff"
                                : undefined,
                            borderRadius: 4,
                          }}
                          onClick={() =>
                            setSelectedFile({
                              name: file.file_name,
                              path: file.source_file,
                            })
                          }
                        >
                          <List.Item.Meta
                            avatar={
                              <FileTextOutlined
                                style={{
                                  fontSize: 20,
                                  color:
                                    selectedFile?.path === file.source_file
                                      ? "#1677ff"
                                      : "#bfbfbf",
                                }}
                              />
                            }
                            title={
                              <span
                                style={{
                                  fontSize: 13,
                                  color:
                                    selectedFile?.path === file.source_file
                                      ? "#1677ff"
                                      : undefined,
                                }}
                              >
                                {file.file_name}
                              </span>
                            }
                            description={`${file.doc_type} | ${file.chunk_count} 段`}
                          />
                          {selectedFile?.path === file.source_file && (
                            <CheckCircleOutlined style={{ color: "#1677ff" }} />
                          )}
                        </List.Item>
                      )}
                    />
                  )}
                </div>
              ),
            },
            {
              key: "session",
              label: "本次生成",
              children: (
                <div>
                  {sessionGeneratedDocs.length === 0 ? (
                    <Typography.Text type="secondary">
                      当前会话暂无已生成文档
                    </Typography.Text>
                  ) : (
                    <List
                      size="small"
                      dataSource={sessionGeneratedDocs}
                      style={{ maxHeight: 320, overflow: "auto" }}
                      renderItem={(docPath) => {
                        const fileName = docPath.split("/").pop() || docPath;
                        return (
                          <List.Item
                            style={{
                              cursor: "pointer",
                              padding: "8px 12px",
                              background:
                                selectedFile?.path === docPath
                                  ? "#e6f7ff"
                                  : undefined,
                              borderRadius: 4,
                            }}
                            onClick={() =>
                              setSelectedFile({
                                name: fileName,
                                path: docPath,
                              })
                            }
                          >
                            <List.Item.Meta
                              avatar={
                                <FileTextOutlined
                                  style={{
                                    fontSize: 20,
                                    color:
                                      selectedFile?.path === docPath
                                        ? "#1677ff"
                                        : "#bfbfbf",
                                  }}
                                />
                              }
                              title={
                                <span
                                  style={{
                                    fontSize: 13,
                                    color:
                                      selectedFile?.path === docPath
                                        ? "#1677ff"
                                        : undefined,
                                  }}
                                >
                                  {fileName}
                                </span>
                              }
                            />
                            {selectedFile?.path === docPath && (
                              <CheckCircleOutlined
                                style={{ color: "#1677ff" }}
                              />
                            )}
                          </List.Item>
                        );
                      }}
                    />
                  )}
                </div>
              ),
            },
          ]}
        />

        {/* Selected file indicator */}
        {selectedFile && (
          <div
            style={{
              padding: "8px 12px",
              background: "#f6ffed",
              borderRadius: 6,
              marginBottom: 12,
              fontSize: 13,
            }}
          >
            <CheckCircleOutlined style={{ color: "#52c41a", marginRight: 8 }} />
            已选择: {selectedFile.name}
          </div>
        )}

        <div style={{ marginTop: "auto", paddingTop: 16 }}>
          <Button
            type="primary"
            block
            disabled={!canGenerate}
            loading={isGeneratingPptx}
            onClick={handleGenerate}
          >
            {isGeneratingPptx ? "生成中..." : "生成 PPT"}
          </Button>
        </div>
      </div>

      {/* Right panel - Result */}
      <div
        className="writing-panel"
        style={{
          flex: 1.2,
          background: "#fff",
          borderRadius: 8,
          padding: 24,
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Typography.Title
          level={5}
          style={{ marginTop: 0, marginBottom: 16 }}
        >
          生成结果
        </Typography.Title>

        {/* Empty state */}
        {!isGeneratingPptx && !isCompleted && !isFailed && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              color: "#bfbfbf",
            }}
          >
            <FileTextOutlined
              style={{ fontSize: 48, marginBottom: 12 }}
            />
            <Typography.Text type="secondary">
              选择文档并点击「生成 PPT」后，结果将在此处显示
            </Typography.Text>
          </div>
        )}

        {/* Generating state */}
        {isGeneratingPptx && !isFailed && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Spin size="large" style={{ marginBottom: 24 }} />
            <GenerationSteps
              currentStep={stepIndex}
              totalSteps={totalSteps}
              error={null}
            />
          </div>
        )}

        {/* Failed state */}
        {isFailed && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <GenerationSteps
              currentStep={stepIndex}
              totalSteps={totalSteps}
              error={pptxError}
            />
            <Alert
              type="error"
              message="生成失败"
              description={pptxError}
              showIcon
              style={{ marginTop: 24, maxWidth: 400, width: "100%" }}
            />
            <Button
              style={{ marginTop: 16 }}
              onClick={() => {
                resetPptxState();
              }}
            >
              重试
            </Button>
          </div>
        )}

        {/* Success state */}
        {isCompleted && pptxResult && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            {/* Summary */}
            <div
              style={{
                padding: "12px 16px",
                background: "#f6ffed",
                borderRadius: 6,
                marginBottom: 16,
              }}
            >
              <Typography.Text
                strong
                style={{ color: "#52c41a", fontSize: 14 }}
              >
                <CheckCircleOutlined style={{ marginRight: 8 }} />
                生成完成
              </Typography.Text>
              <div style={{ marginTop: 4, fontSize: 12, color: "#8c8c8c" }}>
                共 {pptxResult.slide_count} 页幻灯片 &middot; 耗时{" "}
                {(pptxResult.duration_ms / 1000).toFixed(1)}s &middot; 来源:{" "}
                {pptxResult.source_doc.split("/").pop()}
              </div>
            </div>

            {/* Slide thumbnails */}
            {pptxResult.slides.length > 0 && (
              <div
                style={{
                  flex: 1,
                  overflow: "auto",
                  padding: "8px 0",
                }}
              >
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(180px, 1fr))",
                    gap: 12,
                  }}
                >
                  {pptxResult.slides.map((slide, i) => (
                    <SlideThumbnail
                      key={i}
                      slide={slide}
                      index={i}
                      total={pptxResult.slides.length}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Download button */}
            <div
              style={{
                paddingTop: 16,
                borderTop: "1px solid #f0f0f0",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                PPT 已生成，点击下载
              </Typography.Text>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={() => {
                  if (pptxResult.download_url) {
                    window.open(pptxResult.download_url, "_blank");
                  } else {
                    message.info("暂无可下载文件");
                  }
                }}
              >
                下载 .pptx
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
