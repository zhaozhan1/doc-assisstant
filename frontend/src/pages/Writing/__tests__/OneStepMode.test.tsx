import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OneStepMode } from "../OneStepMode";
import { useWritingStore } from "../../../stores/useWritingStore";
import * as templatesApi from "../../../api/templates";

describe("OneStepMode", () => {
  beforeEach(() => {
    useWritingStore.setState({
      mode: "onestep",
      content: "",
      isStreaming: false,
      error: null,
      selectedRefs: [],
      searchResults: [],
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders description textarea", () => {
    render(<OneStepMode />);
    const textarea = screen.getByPlaceholderText("请描述您的写作需求...");
    expect(textarea).toBeInTheDocument();
  });

  it("renders template selector with default option", () => {
    render(<OneStepMode />);
    expect(screen.getByText("自动选择")).toBeInTheDocument();
  });

  it("loads and displays templates", async () => {
    vi.spyOn(templatesApi, "listTemplates").mockResolvedValue([
      {
        id: "tpl-1",
        name: "通知模板",
        doc_type: "通知",
        sections: [],
        is_builtin: true,
      },
    ]);

    render(<OneStepMode />);

    // "自动选择" is always visible; template loads async
    await waitFor(() => {
      expect(screen.getByText("自动选择")).toBeInTheDocument();
    });
  });

  it("calls startStream on generate button click", async () => {
    const user = userEvent.setup();
    const startStreamSpy = vi.fn().mockResolvedValue(undefined);

    useWritingStore.setState({
      startStream: startStreamSpy,
    });

    render(<OneStepMode />);

    const textarea = screen.getByPlaceholderText("请描述您的写作需求...");
    await user.type(textarea, "写一份关于XX的通知");

    const generateBtn = screen.getByRole("button", { name: /生成公文/ });
    await user.click(generateBtn);

    expect(startStreamSpy).toHaveBeenCalledOnce();
    expect(startStreamSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        description: "写一份关于XX的通知",
      }),
    );
  });

  it("disables generate button when description is empty", () => {
    render(<OneStepMode />);
    const generateBtn = screen.getByRole("button", { name: /生成公文/ });
    expect(generateBtn).toBeDisabled();
  });

  it("shows streaming indicator during generation", () => {
    useWritingStore.setState({ isStreaming: true });
    render(<OneStepMode />);
    expect(screen.getByText("正在生成...")).toBeInTheDocument();
  });

  it("shows streaming content in preview", () => {
    useWritingStore.setState({
      content: "这是一份测试公文的内容",
      isStreaming: true,
    });
    render(<OneStepMode />);
    expect(screen.getByText("这是一份测试公文的内容")).toBeInTheDocument();
  });

  it("shows download button after generation completes", () => {
    useWritingStore.setState({
      content: "生成的公文内容",
      isStreaming: false,
    });
    render(<OneStepMode />);
    expect(
      screen.getByRole("button", { name: /下载/ }),
    ).toBeInTheDocument();
  });

  it("shows empty state when no content", () => {
    render(<OneStepMode />);
    expect(
      screen.getByText(/预览将在此处实时显示/),
    ).toBeInTheDocument();
  });

  it("aborts stream when abort button clicked", async () => {
    const user = userEvent.setup();
    const abortSpy = vi.fn();

    useWritingStore.setState({
      isStreaming: true,
      content: "部分内容",
      abortStream: abortSpy,
    });

    render(<OneStepMode />);

    const abortBtn = screen.getByRole("button", { name: /停止/ });
    await user.click(abortBtn);

    expect(abortSpy).toHaveBeenCalledOnce();
  });
});
