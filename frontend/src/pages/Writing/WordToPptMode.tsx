import { useState } from "react";
import { Button, Tabs, Typography, Upload, Input } from "antd";
import {
  InboxOutlined,
  FileTextOutlined,
  SearchOutlined,
} from "@ant-design/icons";

const { Dragger } = Upload;

export function WordToPptMode() {
  const [activeTab, setActiveTab] = useState("upload");

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
          选择 Word 文档
        </Typography.Title>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: "upload",
              label: "上传文件",
              children: (
                <Dragger
                  accept=".docx"
                  beforeUpload={() => false}
                  showUploadList={false}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">
                    点击或拖拽 .docx 文件到此处上传
                  </p>
                </Dragger>
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
                    style={{ marginBottom: 12 }}
                  />
                  <Typography.Text type="secondary">
                    暂无可选文档
                  </Typography.Text>
                </div>
              ),
            },
            {
              key: "session",
              label: "本次生成",
              children: (
                <div>
                  <Typography.Text type="secondary">
                    当前会话暂无已生成文档
                  </Typography.Text>
                </div>
              ),
            },
          ]}
        />

        <div style={{ marginTop: "auto", paddingTop: 16 }}>
          <Button type="primary" disabled block>
            生成 PPT（即将在后续版本支持）
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
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <FileTextOutlined
          style={{ fontSize: 48, marginBottom: 12, color: "#bfbfbf" }}
        />
        <Typography.Text type="secondary">
          Word 转 PPT 功能将在后续版本提供
        </Typography.Text>
      </div>
    </div>
  );
}
