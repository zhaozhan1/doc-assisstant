import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WordToPptMode } from "../WordToPptMode";
import { useWritingStore } from "../../../stores/useWritingStore";

describe("WordToPptMode", () => {
  beforeEach(() => {
    useWritingStore.setState({
      mode: "wordtoppt",
      content: "",
      isStreaming: false,
      error: null,
      selectedRefs: [],
      searchResults: [],
    });
  });

  it("renders 3 source tabs", () => {
    render(<WordToPptMode />);
    expect(screen.getByText("上传文件")).toBeInTheDocument();
    expect(screen.getByText("知识库选择")).toBeInTheDocument();
    expect(screen.getByText("本次生成")).toBeInTheDocument();
  });

  it("shows upload area in default tab", () => {
    render(<WordToPptMode />);
    expect(
      screen.getByText(/点击或拖拽 .docx 文件到此处/),
    ).toBeInTheDocument();
  });

  it("shows disabled generate button", () => {
    render(<WordToPptMode />);
    const btn = screen.getByRole("button", { name: /生成 PPT/ });
    expect(btn).toBeDisabled();
  });

  it("shows placeholder text in right panel", () => {
    render(<WordToPptMode />);
    expect(
      screen.getByText(/Word 转 PPT 功能将在后续版本提供/),
    ).toBeInTheDocument();
  });

  it("switches to knowledge base tab", async () => {
    const user = userEvent.setup();
    render(<WordToPptMode />);

    await user.click(screen.getByText("知识库选择"));
    // Should show KB-related UI (search input)
    expect(
      screen.getByPlaceholderText("搜索知识库中的文档..."),
    ).toBeInTheDocument();
  });

  it("switches to session-generated tab", async () => {
    const user = userEvent.setup();
    render(<WordToPptMode />);

    await user.click(screen.getByText("本次生成"));
    expect(
      screen.getByText(/当前会话暂无已生成文档/),
    ).toBeInTheDocument();
  });
});
