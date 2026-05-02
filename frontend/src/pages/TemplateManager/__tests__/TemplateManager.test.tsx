import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TemplateManager from "../index";
import type { TemplateDef } from "../../../types/api";

// ---- Mock data ----
const builtinTemplates: TemplateDef[] = [
  {
    id: "tpl-1",
    name: "通知模板",
    doc_type: "notice",
    sections: [
      { title: "标题", writing_points: ["简洁明了"], format_rules: ["居中"] },
      { title: "正文", writing_points: ["说明事项"], format_rules: ["首行缩进"] },
      { title: "落款", writing_points: ["单位+日期"], format_rules: ["右对齐"] },
    ],
    is_builtin: true,
  },
  {
    id: "tpl-2",
    name: "报告模板",
    doc_type: "report",
    sections: [
      { title: "标题", writing_points: ["包含主题"], format_rules: ["居中"] },
      { title: "正文", writing_points: ["事实陈述"], format_rules: ["首行缩进"] },
    ],
    is_builtin: true,
  },
];

const customTemplates: TemplateDef[] = [
  {
    id: "tpl-custom-1",
    name: "自定义通知",
    doc_type: "notice",
    sections: [
      { title: "开头", writing_points: ["问候"], format_rules: ["顶格"] },
      { title: "内容", writing_points: ["详情"], format_rules: ["缩进"] },
    ],
    is_builtin: false,
  },
];

const allTemplates = [...builtinTemplates, ...customTemplates];

const mockListTemplates = vi.fn();

vi.mock("../../../api/templates", () => ({
  get listTemplates() {
    return mockListTemplates;
  },
}));

describe("TemplateManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListTemplates.mockResolvedValue(allTemplates);
  });

  it("renders filter tabs (全部 / 内置模板 / 自定义模板)", async () => {
    render(<TemplateManager />);

    await waitFor(() => {
      expect(screen.getByText("全部")).toBeInTheDocument();
    });
    expect(screen.getByText("内置模板")).toBeInTheDocument();
    expect(screen.getByText("自定义模板")).toBeInTheDocument();
  });

  it("renders template cards in grid layout", async () => {
    render(<TemplateManager />);

    await waitFor(() => {
      expect(screen.getByText("通知模板")).toBeInTheDocument();
    });
    expect(screen.getByText("报告模板")).toBeInTheDocument();
    expect(screen.getByText("自定义通知")).toBeInTheDocument();
  });

  it("distinguishes built-in vs custom templates", async () => {
    render(<TemplateManager />);

    await waitFor(() => {
      expect(screen.getAllByText("内置").length).toBeGreaterThanOrEqual(2);
    });
    expect(screen.getByText("自定义")).toBeInTheDocument();
  });

  it("shows section count on each card", async () => {
    render(<TemplateManager />);

    await waitFor(() => {
      // 通知模板 has 3 sections
      expect(screen.getByText("3 个段落")).toBeInTheDocument();
    });
    // 报告模板 and 自定义通知 both have 2 sections -> at least one "2 个段落"
    expect(screen.getAllByText("2 个段落").length).toBeGreaterThanOrEqual(1);
  });

  it("shows separate sections for built-in and custom templates", async () => {
    render(<TemplateManager />);

    await waitFor(() => {
      // Section headers with counts
      expect(screen.getByText(/内置模板.*2/)).toBeInTheDocument();
      expect(screen.getByText(/自定义模板.*1/)).toBeInTheDocument();
    });
  });

  it("filters to show only built-in templates when 内置模板 tab selected", async () => {
    const user = userEvent.setup();
    render(<TemplateManager />);

    await waitFor(() => {
      expect(screen.getByText("通知模板")).toBeInTheDocument();
    });

    await user.click(screen.getByText("内置模板"));

    // Custom template should not be visible
    await waitFor(() => {
      expect(screen.queryByText("自定义通知")).not.toBeInTheDocument();
    });
    // Built-in templates should still be visible
    expect(screen.getByText("通知模板")).toBeInTheDocument();
  });

  it("opens editor modal on 新建模板 click", async () => {
    const user = userEvent.setup();
    render(<TemplateManager />);

    await waitFor(() => {
      expect(screen.getByText("通知模板")).toBeInTheDocument();
    });

    const newBtn = screen.getByText("+ 新建模板");
    await user.click(newBtn);

    await waitFor(() => {
      expect(screen.getByText("新建模板")).toBeInTheDocument();
    });
  });

  it("delete button triggers confirmation for custom template", async () => {
    render(<TemplateManager />);

    await waitFor(() => {
      expect(screen.getByText("自定义通知")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("删除");
    expect(deleteButtons.length).toBeGreaterThanOrEqual(1);

    const user = userEvent.setup();
    await user.click(deleteButtons[0]);

    // Popconfirm should appear
    await waitFor(() => {
      expect(screen.getByText("确定删除该模板吗？")).toBeInTheDocument();
    });
  });

  it("edit button opens editor with pre-filled data", async () => {
    const user = userEvent.setup();
    render(<TemplateManager />);

    await waitFor(() => {
      expect(screen.getByText("自定义通知")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole("button", { name: /编辑/ });
    await user.click(editButtons[0]);

    await waitFor(() => {
      // Modal title should be "编辑模板"
      expect(screen.getByText("编辑模板")).toBeInTheDocument();
    });

    // Name field should be pre-filled
    const nameInput = screen.getByDisplayValue("自定义通知");
    expect(nameInput).toBeInTheDocument();
  });
});
