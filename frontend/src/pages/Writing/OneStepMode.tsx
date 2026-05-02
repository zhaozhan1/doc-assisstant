import { useState, useEffect, useCallback } from "react";
import { Button, Select, Typography, message } from "antd";
import { FileTextOutlined, StopOutlined } from "@ant-design/icons";
import Markdown from "react-markdown";
import { useWritingStore } from "../../stores/useWritingStore";
import { listTemplates } from "../../api/templates";
import { downloadFile } from "../../api/files";
import type { TemplateDef } from "../../types/api";

export function OneStepMode() {
  const content = useWritingStore((s) => s.content);
  const isStreaming = useWritingStore((s) => s.isStreaming);
  const startStream = useWritingStore((s) => s.startStream);
  const abortStream = useWritingStore((s) => s.abortStream);

  const [description, setDescription] = useState("");
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateDef[]>([]);

  useEffect(() => {
    listTemplates()
      .then(setTemplates)
      .catch(() => {
        /* ignore template load errors */
      });
  }, []);

  const handleGenerate = useCallback(() => {
    if (!description.trim()) return;
    startStream({
      description: description.trim(),
      template_id: templateId,
    });
  }, [description, templateId, startStream]);

  return (
    <div style={{ display: "flex", gap: 16, height: "100%" }}>
      {/* Left panel */}
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
          写作需求
        </Typography.Title>

        <textarea
          placeholder="请描述您的写作需求..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{
            flex: 1,
            minHeight: 160,
            border: "1px solid #d9d9d9",
            borderRadius: 6,
            padding: "8px 12px",
            fontSize: 14,
            resize: "vertical",
            outline: "none",
            fontFamily: "inherit",
          }}
        />

        <div style={{ marginTop: 12 }}>
          <Select
            value={templateId ?? undefined}
            onChange={(val) => setTemplateId(val ?? null)}
            style={{ width: "100%" }}
            placeholder="自动选择"
            allowClear
          >
            {templates.map((t) => (
              <Select.Option key={t.id} value={t.id}>
                {t.name}
              </Select.Option>
            ))}
          </Select>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 16,
          }}
        >
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            预计参考 5-10 份历史文档
          </Typography.Text>
          <Button
            type="primary"
            onClick={handleGenerate}
            disabled={!description.trim() || isStreaming}
          >
            生成公文
          </Button>
        </div>
      </div>

      {/* Right panel */}
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
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Typography.Title level={5} style={{ margin: 0 }}>
              生成预览
            </Typography.Title>
            {isStreaming && (
              <>
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "#52c41a",
                    display: "inline-block",
                  }}
                />
                <Typography.Text type="secondary">
                  正在生成...
                </Typography.Text>
              </>
            )}
          </div>
          {isStreaming && (
            <Button
              size="small"
              icon={<StopOutlined />}
              onClick={abortStream}
            >
              停止
            </Button>
          )}
        </div>

        {content ? (
          <>
            <div
              style={{
                flex: 1,
                overflow: "auto",
                padding: "12px 0",
                lineHeight: 1.8,
              }}
            >
              <Markdown>{content}</Markdown>
              {isStreaming && (
                <span
                  style={{
                    display: "inline-block",
                    width: 2,
                    height: 16,
                    background: "#1677ff",
                    animation: "blink 1s infinite",
                    verticalAlign: "middle",
                    marginLeft: 2,
                  }}
                />
              )}
            </div>
            {!isStreaming && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  paddingTop: 12,
                  borderTop: "1px solid #f0f0f0",
                }}
              >
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  已参考历史文档
                </Typography.Text>
                <Button
                  type="primary"
                  onClick={() => {
                    const outputPath =
                      useWritingStore.getState().outputPath;
                    if (outputPath) {
                      window.open(downloadFile(outputPath), "_blank");
                    } else {
                      message.info("暂无可下载文件");
                    }
                  }}
                >
                  下载 .docx
                </Button>
              </div>
            )}
          </>
        ) : (
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
            <FileTextOutlined style={{ fontSize: 48, marginBottom: 12 }} />
            <Typography.Text type="secondary">
              点击「生成公文」后，预览将在此处实时显示
            </Typography.Text>
          </div>
        )}
      </div>

      <style>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}
