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
      pptxTaskId: null,
      pptxResult: null,
      pptxError: null,
      isGeneratingPptx: false,
      sessionGeneratedDocs: [],
    });
  });

  it("renders 3 source tabs", () => {
    render(<WordToPptMode />);
    expect(screen.getByText("上传文件")).toBeInTheDocument();
    expect(screen.getByText("知识库选择")).toBeInTheDocument();
    expect(screen.getByText("本次生成")).toBeInTheDocument();
  });

  it("shows KB search in default tab", () => {
    render(<WordToPptMode />);
    expect(
      screen.getByPlaceholderText("搜索知识库中的文档..."),
    ).toBeInTheDocument();
  });

  it("shows disabled generate button when no file selected", () => {
    render(<WordToPptMode />);
    const btn = screen.getByRole("button", { name: /生成 PPT/ });
    expect(btn).toBeDisabled();
  });

  it("shows placeholder text in right panel", () => {
    render(<WordToPptMode />);
    expect(
      screen.getByText(/选择文档并点击「生成 PPT」后，结果将在此处显示/),
    ).toBeInTheDocument();
  });

  it("switches to upload tab and shows drag area", async () => {
    const user = userEvent.setup();
    render(<WordToPptMode />);

    await user.click(screen.getByText("上传文件"));
    expect(
      screen.getByText(/点击或拖拽 .docx 文件到此处/),
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
