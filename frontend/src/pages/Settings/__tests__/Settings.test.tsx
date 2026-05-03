import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Settings from "../index";
import type {
  KBSettings,
  LLMSettings,
  GenerationSettings,
  OnlineSearchConfig,
} from "../../../types/api";

// ---- Mock data ----
const mockKB: KBSettings = {
  source_folder: "/data/source",
  db_path: "/data/chromadb",
  chunk_size: 500,
  chunk_overlap: 50,
};

const mockLLM: LLMSettings = {
  default_provider: "openai",
  embed_provider: "openai",
  ollama_base_url: "http://localhost:11434",
  ollama_chat_model: "qwen2.5",
  ollama_embed_model: "bge-large-zh-v1.5",
  claude_base_url: "https://api.anthropic.com",
  claude_api_key: "sk-test-secret-key",
  claude_chat_model: "claude-sonnet-4-20250514",
  openai_base_url: "http://127.0.0.1:18008/v1",
  openai_api_key: "test-key",
  openai_chat_model: "Qwen3.6-35B-A3B-MLX-8bit",
  openai_embed_model: "bge-m3-mlx-fp16",
};

const mockGeneration: GenerationSettings = {
  output_format: "docx",
  save_path: "/data/output",
  include_sources: true,
  word_template_path: "/data/template.dotx",
};

const mockOnlineSearch: OnlineSearchConfig = {
  enabled: true,
  provider: "baidu",
  api_key: "search-api-key",
  base_url: "https://api.bing.microsoft.com",
  domains: ["gov.cn", "example.com"],
  max_results: 5,
};

// ---- Store mock ----
let mockStoreState: Record<string, unknown>;

const mockFetchAllConfigs = vi.fn().mockResolvedValue(undefined);
const mockUpdateKB = vi.fn().mockResolvedValue(undefined);
const mockUpdateLLM = vi.fn().mockResolvedValue(undefined);
const mockUpdateGeneration = vi.fn().mockResolvedValue(undefined);
const mockUpdateOnlineSearch = vi.fn().mockResolvedValue(undefined);
const mockTestConnection = vi.fn().mockResolvedValue({
  success: true,
  message: "连接成功",
});
const mockBrowseDirectory = vi.fn().mockResolvedValue({
  path: "/data",
  children: [
    { name: "source", path: "/data/source", is_dir: true },
    { name: "output", path: "/data/output", is_dir: true },
  ],
});

function resetMockState() {
  mockStoreState = {
    kb: mockKB,
    llm: mockLLM,
    generation: mockGeneration,
    onlineSearch: mockOnlineSearch,
    loading: false,
    error: null,
    fetchAllConfigs: mockFetchAllConfigs,
    updateKB: mockUpdateKB,
    updateLLM: mockUpdateLLM,
    updateGeneration: mockUpdateGeneration,
    updateOnlineSearch: mockUpdateOnlineSearch,
    testConnection: mockTestConnection,
    browseDirectory: mockBrowseDirectory,
  };
}

vi.mock("../../../stores/useSettingsStore", () => ({
  useSettingsStore: Object.assign(
    (selector?: (state: Record<string, unknown>) => unknown) =>
      selector ? selector(mockStoreState) : mockStoreState,
    { getState: vi.fn(), setState: vi.fn(), subscribe: vi.fn() },
  ),
}));

describe("Settings Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetMockState();
  });

  it("renders 4 tabs", () => {
    render(<Settings />);
    expect(screen.getByText("知识库")).toBeInTheDocument();
    expect(screen.getByText("LLM")).toBeInTheDocument();
    expect(screen.getByText("在线检索")).toBeInTheDocument();
    expect(screen.getByText("输出")).toBeInTheDocument();
  });

  it("loads configs on mount (calls fetchAllConfigs)", () => {
    render(<Settings />);
    expect(mockFetchAllConfigs).toHaveBeenCalledOnce();
  });

  it("renders KB config form fields", () => {
    render(<Settings />);
    // KB tab is the default active tab - check form labels
    expect(screen.getByText("源文件夹路径")).toBeInTheDocument();
    expect(screen.getByText("数据库路径")).toBeInTheDocument();
    expect(screen.getByText("分块大小（字）")).toBeInTheDocument();
    expect(screen.getByText("分块重叠（字）")).toBeInTheDocument();
    // Browse button exists
    expect(screen.getByText("浏览")).toBeInTheDocument();
    // Save button exists (Ant Design inserts spaces between CJK chars)
    const saveButton = screen.getByText((content) =>
      content.replace(/\s/g, "").includes("保存"),
    );
    expect(saveButton).toBeInTheDocument();
  });

  it("renders LLM config form with conditional fields for selected provider", async () => {
    const user = userEvent.setup();
    render(<Settings />);

    await user.click(screen.getByText("LLM"));

    expect(screen.getByText("聊天提供商")).toBeInTheDocument();
    expect(screen.getByText("Embedding 提供商")).toBeInTheDocument();

    // Default provider is "openai", so OpenAI fields should be visible
    expect(screen.getByText("Chat Model")).toBeInTheDocument();
    expect(screen.getByText("Base URL")).toBeInTheDocument();
    expect(screen.getByText("API Key")).toBeInTheDocument();
  });

  it("renders Online Search config with Switch and test connection button", async () => {
    const user = userEvent.setup();
    render(<Settings />);

    // Switch to Online Search tab
    await user.click(screen.getByText("在线检索"));

    expect(screen.getByText("启用在线检索")).toBeInTheDocument();
    expect(screen.getByText("搜索提供商")).toBeInTheDocument();
    expect(screen.getByText("API Key")).toBeInTheDocument();
    expect(screen.getByText("Base URL")).toBeInTheDocument();
    expect(screen.getByText("搜索域名限制")).toBeInTheDocument();
    expect(screen.getByText("最大结果数")).toBeInTheDocument();
    // Ant Design inserts spaces in button text
    const testConnBtn = screen.getByText((content) =>
      content.replace(/\s/g, "") === "测试连接",
    );
    expect(testConnBtn).toBeInTheDocument();
  });

  it("renders Output config form fields", async () => {
    const user = userEvent.setup();
    render(<Settings />);

    // Switch to Output tab
    await user.click(screen.getByText("输出"));

    expect(screen.getByText("输出格式")).toBeInTheDocument();
    expect(screen.getByText("保存路径")).toBeInTheDocument();
    expect(screen.getByText("包含来源引用")).toBeInTheDocument();
    expect(screen.getByText("Word 模板路径")).toBeInTheDocument();
  });

  it("Save button on KB tab calls updateKB", async () => {
    const user = userEvent.setup();
    render(<Settings />);

    // KB tab is active by default - Ant Design inserts spaces in button text
    const saveBtn = screen.getByText((content) =>
      content.replace(/\s/g, "") === "保存",
    );
    await user.click(saveBtn);
    expect(mockUpdateKB).toHaveBeenCalledOnce();
  });

  it("Save button on LLM tab calls updateLLM", async () => {
    const user = userEvent.setup();
    render(<Settings />);

    await user.click(screen.getByText("LLM"));
    // Wait for tab panel to render
    await waitFor(() => {
      expect(screen.getByText("聊天提供商")).toBeInTheDocument();
    });
    // Multiple "保存" buttons may exist; use getAllBy and click the visible one
    const saveBtns = screen.getAllByText((content) =>
      content.replace(/\s/g, "") === "保存",
    );
    // Click the last one (most recently rendered, in the active tab)
    await user.click(saveBtns[saveBtns.length - 1]);
    expect(mockUpdateLLM).toHaveBeenCalledOnce();
  });

  it("Browse button calls browseDirectory", async () => {
    const user = userEvent.setup();
    render(<Settings />);

    const browseButtons = screen.getAllByText("浏览");
    await user.click(browseButtons[0]);
    expect(mockBrowseDirectory).toHaveBeenCalled();
  });

  it("Test connection button calls testConnection", async () => {
    const user = userEvent.setup();
    render(<Settings />);

    await user.click(screen.getByText("在线检索"));
    const testConnBtn = screen.getByText((content) =>
      content.replace(/\s/g, "") === "测试连接",
    );
    await user.click(testConnBtn);
    expect(mockTestConnection).toHaveBeenCalledOnce();
  });

  it("displays error state", () => {
    mockStoreState.error = "加载配置失败";
    render(<Settings />);
    expect(screen.getByText("加载配置失败")).toBeInTheDocument();
  });
});
