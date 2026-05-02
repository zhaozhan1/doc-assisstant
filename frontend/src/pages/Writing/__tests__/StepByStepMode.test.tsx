import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StepByStepMode } from "../StepByStepMode";
import { useWritingStore } from "../../../stores/useWritingStore";
import * as searchApi from "../../../api/search";

describe("StepByStepMode", () => {
  beforeEach(() => {
    useWritingStore.setState({
      mode: "stepbystep",
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

  it("renders direction textarea", () => {
    render(<StepByStepMode />);
    expect(
      screen.getByPlaceholderText("请描述写作方向..."),
    ).toBeInTheDocument();
  });

  it("renders keyword input area", () => {
    render(<StepByStepMode />);
    expect(screen.getByPlaceholderText("输入关键词后回车")).toBeInTheDocument();
  });

  it("adds keyword tags on enter", async () => {
    const user = userEvent.setup();
    render(<StepByStepMode />);

    const input = screen.getByPlaceholderText("输入关键词后回车");
    await user.type(input, "环保{Enter}");

    expect(screen.getByText("环保")).toBeInTheDocument();
  });

  it("removes keyword tag on close click", async () => {
    const user = userEvent.setup();
    render(<StepByStepMode />);

    const input = screen.getByPlaceholderText("输入关键词后回车");
    await user.type(input, "环保{Enter}");
    expect(screen.getByText("环保")).toBeInTheDocument();

    // Click the close icon on the tag
    const removeBtn = screen.getByRole("img", { name: /Close/i });
    await user.click(removeBtn);
    expect(screen.queryByText("环保")).not.toBeInTheDocument();
  });

  it("calls search API on search button click", async () => {
    const user = userEvent.setup();
    const setSearchResultsSpy = vi.fn();

    vi.spyOn(searchApi, "search").mockResolvedValue([
      {
        source_type: "local" as const,
        title: "关于XX的通知",
        content: "内容",
        score: 0.9,
        metadata: {},
      },
    ]);

    useWritingStore.setState({
      setSearchResults: setSearchResultsSpy,
    });

    render(<StepByStepMode />);

    const directionArea = screen.getByPlaceholderText("请描述写作方向...");
    await user.type(directionArea, "关于环保工作的通知");

    const searchBtn = screen.getByRole("button", { name: /检索素材/ });
    await user.click(searchBtn);

    expect(searchApi.search).toHaveBeenCalledOnce();
  });

  it("renders search results with checkboxes after search", async () => {
    const mockResults = [
      {
        source_type: "local" as const,
        title: "关于环保的通知",
        content: "内容",
        score: 0.9,
        metadata: {},
      },
      {
        source_type: "online" as const,
        title: "环保政策文件",
        content: "在线内容",
        score: 0.8,
        metadata: {},
      },
    ];

    // Set results directly in store
    useWritingStore.setState({ searchResults: mockResults });

    render(<StepByStepMode />);

    expect(screen.getByText("关于环保的通知")).toBeInTheDocument();
    expect(screen.getByText("环保政策文件")).toBeInTheDocument();
  });

  it("allows selecting and deselecting results", async () => {
    const user = userEvent.setup();
    const setSelectedRefsSpy = vi.fn();

    useWritingStore.setState({
      searchResults: [
        {
          source_type: "local" as const,
          title: "关于环保的通知",
          content: "内容",
          score: 0.9,
          metadata: {},
        },
      ],
      setSelectedRefs: setSelectedRefsSpy,
    });

    render(<StepByStepMode />);

    const checkbox = screen.getByRole("checkbox");
    await user.click(checkbox);

    expect(setSelectedRefsSpy).toHaveBeenCalled();
  });

  it("renders supplementary requirements textarea", () => {
    render(<StepByStepMode />);
    expect(
      screen.getByPlaceholderText("补充写作要求（可选）..."),
    ).toBeInTheDocument();
  });

  it("calls startStream on generate with selected refs", async () => {
    const user = userEvent.setup();
    const startStreamSpy = vi.fn().mockResolvedValue(undefined);

    useWritingStore.setState({
      selectedRefs: ["关于环保的通知"],
      searchResults: [
        {
          source_type: "local" as const,
          title: "关于环保的通知",
          content: "内容",
          score: 0.9,
          metadata: {},
        },
      ],
      startStream: startStreamSpy,
    });

    render(<StepByStepMode />);

    const directionArea = screen.getByPlaceholderText("请描述写作方向...");
    await user.type(directionArea, "关于环保的通知");

    const generateBtn = screen.getByRole("button", { name: /生成公文/ });
    await user.click(generateBtn);

    expect(startStreamSpy).toHaveBeenCalledOnce();
    expect(startStreamSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        description: "关于环保的通知",
        selected_refs: ["关于环保的通知"],
      }),
    );
  });

  it("shows empty preview state", () => {
    render(<StepByStepMode />);
    expect(
      screen.getByText(/选择素材并点击「生成公文」后/),
    ).toBeInTheDocument();
  });

  it("shows result counter after search", () => {
    useWritingStore.setState({
      searchResults: [
        {
          source_type: "local" as const,
          title: "文档1",
          content: "内容",
          score: 0.9,
          metadata: {},
        },
        {
          source_type: "local" as const,
          title: "文档2",
          content: "内容",
          score: 0.8,
          metadata: {},
        },
      ],
    });

    render(<StepByStepMode />);
    expect(screen.getByText(/检索结果（2 条）/)).toBeInTheDocument();
  });
});
