import { useState, useCallback } from "react";
import { Button, Tag, Typography, Checkbox, message } from "antd";
import {
  FileTextOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import Markdown from "react-markdown";
import { useWritingStore } from "../../stores/useWritingStore";
import { search } from "../../api/search";
import { downloadFile } from "../../api/files";
import type { UnifiedSearchResult } from "../../types/api";

function SearchResultList({
  results,
  selectedRefs,
  onToggle,
}: {
  results: UnifiedSearchResult[];
  selectedRefs: string[];
  onToggle: (title: string) => void;
}) {
  const localResults = results.filter((r) => r.source_type === "local");
  const onlineResults = results.filter((r) => r.source_type === "online");
  return (
    <div style={{ flex: 1, overflow: "auto", marginBottom: 12 }}>
      {localResults.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, paddingLeft: 4 }}>
            <Tag color="blue" style={{ margin: 0 }}>本地知识库</Tag>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{localResults.length} 条</Typography.Text>
          </div>
          {localResults.map((result, idx) => (
            <SearchResultItem key={`local-${idx}`} result={result} selectedRefs={selectedRefs} onToggle={onToggle} />
          ))}
        </div>
      )}
      {onlineResults.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, paddingLeft: 4 }}>
            <Tag color="green" style={{ margin: 0 }}>在线搜索</Tag>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{onlineResults.length} 条</Typography.Text>
          </div>
          {onlineResults.map((result, idx) => (
            <SearchResultItem key={`online-${idx}`} result={result} selectedRefs={selectedRefs} onToggle={onToggle} />
          ))}
        </div>
      )}
    </div>
  );
}

function SearchResultItem({
  result,
  selectedRefs,
  onToggle,
}: {
  result: UnifiedSearchResult;
  selectedRefs: string[];
  onToggle: (title: string) => void;
}) {
  const isSelected = selectedRefs.includes(result.title);
  return (
    <div
      style={{
        padding: "8px 12px",
        marginBottom: 4,
        borderRadius: 6,
        background: isSelected ? "#e6f4ff" : "#fafafa",
        cursor: "pointer",
      }}
      onClick={() => onToggle(result.title)}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Checkbox checked={isSelected} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Typography.Text
            strong
            ellipsis
            style={{ fontSize: 13, display: "block" }}
          >
            {result.title}
          </Typography.Text>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <Typography.Text
              type="secondary"
              style={{ fontSize: 12 }}
            >
              {(result.score * 100).toFixed(0)}%
            </Typography.Text>
            {result.source_type === "online" && typeof result.metadata?.url === "string" && (
              <Typography.Link
                href={result.metadata.url as string}
                target="_blank"
                style={{ fontSize: 11 }}
                onClick={(e) => e.stopPropagation()}
              >
                来源
              </Typography.Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

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
      selected_ref_contents:
        selectedRefs.length > 0
          ? searchResults
              .filter((r) => selectedRefs.includes(r.title))
              .map((r) => ({ title: r.title, content: r.content }))
          : undefined,
      requirements: requirements.trim() || undefined,
    });
  }, [direction, selectedRefs, searchResults, requirements, startStream]);

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

        {searchResults.length > 0 && <SearchResultList results={searchResults} selectedRefs={selectedRefs} onToggle={handleToggleRef} />}

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
          <>
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
              选择素材并点击「生成公文」后，预览将在此处实时显示
            </Typography.Text>
          </div>
        )}
      </div>
    </div>
  );
}
