import { useState, useCallback } from "react";
import { Button, Tag, Typography, Checkbox } from "antd";
import {
  FileTextOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import Markdown from "react-markdown";
import { useWritingStore } from "../../stores/useWritingStore";
import { search } from "../../api/search";

export function StepByStepMode() {
  const content = useWritingStore((s) => s.content);
  const isStreaming = useWritingStore((s) => s.isStreaming);
  const searchResults = useWritingStore((s) => s.searchResults);
  const selectedRefs = useWritingStore((s) => s.selectedRefs);
  const setSearchResults = useWritingStore((s) => s.setSearchResults);
  const setSelectedRefs = useWritingStore((s) => s.setSelectedRefs);
  const startStream = useWritingStore((s) => s.startStream);

  const [direction, setDirection] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [requirements, setRequirements] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  const handleAddKeyword = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && keywordInput.trim()) {
        e.preventDefault();
        const kw = keywordInput.trim();
        if (!keywords.includes(kw)) {
          setKeywords((prev) => [...prev, kw]);
        }
        setKeywordInput("");
      }
    },
    [keywordInput, keywords],
  );

  const handleRemoveKeyword = useCallback((kw: string) => {
    setKeywords((prev) => prev.filter((k) => k !== kw));
  }, []);

  const handleSearch = useCallback(async () => {
    if (!direction.trim()) return;
    setIsSearching(true);
    try {
      const query = keywords.length > 0 ? keywords.join(" ") : direction;
      const results = await search({ query });
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [direction, keywords, setSearchResults]);

  const handleToggleRef = useCallback(
    (title: string) => {
      const newRefs = selectedRefs.includes(title)
        ? selectedRefs.filter((r) => r !== title)
        : [...selectedRefs, title];
      setSelectedRefs(newRefs);
    },
    [selectedRefs, setSelectedRefs],
  );

  const handleGenerate = useCallback(() => {
    if (!direction.trim()) return;
    startStream({
      description: direction.trim(),
      selected_refs:
        selectedRefs.length > 0 ? selectedRefs : undefined,
      requirements: requirements.trim() || undefined,
    });
  }, [direction, selectedRefs, requirements, startStream]);

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
          overflow: "auto",
        }}
      >
        <Typography.Title
          level={5}
          style={{ marginTop: 0, marginBottom: 12 }}
        >
          写作方向
        </Typography.Title>
        <textarea
          placeholder="请描述写作方向..."
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          style={{
            minHeight: 80,
            border: "1px solid #d9d9d9",
            borderRadius: 6,
            padding: "8px 12px",
            fontSize: 14,
            resize: "vertical",
            outline: "none",
            fontFamily: "inherit",
            marginBottom: 12,
          }}
        />

        <Typography.Text
          strong
          style={{ fontSize: 13, marginBottom: 4, display: "block" }}
        >
          检索关键词
        </Typography.Text>
        <Typography.Text
          type="secondary"
          style={{ fontSize: 12, marginBottom: 8, display: "block" }}
        >
          留空则自动提取
        </Typography.Text>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 4,
            marginBottom: 8,
            border: "1px solid #d9d9d9",
            borderRadius: 6,
            padding: "4px 8px",
            minHeight: 36,
            alignItems: "center",
          }}
        >
          {keywords.map((kw) => (
            <Tag
              key={kw}
              closable
              onClose={() => handleRemoveKeyword(kw)}
              style={{ margin: 0 }}
            >
              {kw}
            </Tag>
          ))}
          <input
            placeholder="输入关键词后回车"
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            onKeyDown={handleAddKeyword}
            style={{
              border: "none",
              outline: "none",
              flex: 1,
              minWidth: 120,
              fontSize: 14,
              padding: "2px 0",
            }}
          />
        </div>

        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleSearch}
          loading={isSearching}
          disabled={!direction.trim()}
          style={{ marginBottom: 16 }}
        >
          检索素材
        </Button>

        {searchResults.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <Typography.Text strong style={{ fontSize: 13 }}>
              检索结果（{searchResults.length} 条）— 已选{" "}
              {selectedRefs.length} 份
            </Typography.Text>
          </div>
        )}

        {searchResults.length > 0 && (
          <div
            style={{
              flex: 1,
              overflow: "auto",
              marginBottom: 12,
            }}
          >
            {searchResults.map((result, idx) => (
              <div
                key={idx}
                style={{
                  padding: "8px 12px",
                  marginBottom: 4,
                  borderRadius: 6,
                  background: selectedRefs.includes(result.title)
                    ? "#e6f4ff"
                    : "#fafafa",
                  cursor: "pointer",
                }}
                onClick={() => handleToggleRef(result.title)}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <Checkbox
                    checked={selectedRefs.includes(result.title)}
                  />
                  <div style={{ flex: 1 }}>
                    <Typography.Text strong>
                      {result.title}
                    </Typography.Text>
                    <div>
                      <Tag
                        color={
                          result.source_type === "local"
                            ? "blue"
                            : "green"
                        }
                        style={{ marginRight: 4 }}
                      >
                        {result.source_type === "local"
                          ? "本地"
                          : "在线"}
                      </Tag>
                      <Typography.Text
                        type="secondary"
                        style={{ fontSize: 12 }}
                      >
                        {(result.score * 100).toFixed(0)}%
                      </Typography.Text>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <Typography.Title
          level={5}
          style={{ marginTop: 8, marginBottom: 8 }}
        >
          补充写作要求
        </Typography.Title>
        <textarea
          placeholder="补充写作要求（可选）..."
          value={requirements}
          onChange={(e) => setRequirements(e.target.value)}
          style={{
            minHeight: 60,
            border: "1px solid #d9d9d9",
            borderRadius: 6,
            padding: "8px 12px",
            fontSize: 14,
            resize: "vertical",
            outline: "none",
            fontFamily: "inherit",
            marginBottom: 12,
          }}
        />

        <Button
          type="primary"
          onClick={handleGenerate}
          disabled={!direction.trim() || isStreaming}
        >
          生成公文
        </Button>
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
        {content ? (
          <div
            style={{
              flex: 1,
              overflow: "auto",
              padding: "12px 0",
              lineHeight: 1.8,
            }}
          >
            <Typography.Title level={5} style={{ marginTop: 0 }}>
              生成预览
            </Typography.Title>
            <Markdown>{content}</Markdown>
          </div>
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
              选择素材并点击「生成公文」后，预览将在此处实时显示
            </Typography.Text>
          </div>
        )}
      </div>
    </div>
  );
}
