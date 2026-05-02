import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Writing } from "../index";
import { useWritingStore } from "../../../stores/useWritingStore";

describe("Writing", () => {
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

  it("renders mode switch tabs", () => {
    render(<Writing />);
    expect(screen.getByText("一步生成")).toBeInTheDocument();
    expect(screen.getByText("分步检索")).toBeInTheDocument();
    expect(screen.getByText("Word→PPT")).toBeInTheDocument();
  });

  it("shows one-step mode by default", () => {
    render(<Writing />);
    expect(screen.getByText("写作需求")).toBeInTheDocument();
  });

  it("switches to step-by-step mode on tab click", async () => {
    const user = userEvent.setup();
    render(<Writing />);

    await user.click(screen.getByText("分步检索"));
    expect(useWritingStore.getState().mode).toBe("stepbystep");
  });

  it("switches to Word-to-PPT mode on tab click", async () => {
    const user = userEvent.setup();
    render(<Writing />);

    await user.click(screen.getByText("Word→PPT"));
    expect(useWritingStore.getState().mode).toBe("wordtoppt");
  });

  it("renders left-right split layout", () => {
    const { container } = render(<Writing />);
    const panels = container.querySelectorAll(".writing-panel");
    expect(panels.length).toBe(2);
  });
});
