import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TemplateEditor from "../TemplateEditor";
import type { TemplateDef } from "../../../types/api";

const mockOnSave = vi.fn();
const mockOnCancel = vi.fn();

const existingTemplate: TemplateDef = {
  id: "tpl-edit-1",
  name: "编辑测试模板",
  doc_type: "notice",
  sections: [
    {
      title: "标题段",
      writing_points: ["简洁"],
      format_rules: ["居中"],
    },
    {
      title: "正文段",
      writing_points: ["详细说明"],
      format_rules: ["首行缩进"],
    },
  ],
  is_builtin: false,
};

describe("TemplateEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders modal with title 新建模板 when no template provided", () => {
    render(
      <TemplateEditor open={true} onSave={mockOnSave} onCancel={mockOnCancel} />,
    );

    expect(screen.getByText("新建模板")).toBeInTheDocument();
  });

  it("renders modal with title 编辑模板 when template provided", () => {
    render(
      <TemplateEditor
        open={true}
        template={existingTemplate}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByText("编辑模板")).toBeInTheDocument();
  });

  it("renders form fields: 模板名称, 公文类型, 结构大纲", () => {
    render(
      <TemplateEditor open={true} onSave={mockOnSave} onCancel={mockOnCancel} />,
    );

    expect(screen.getByText("模板名称")).toBeInTheDocument();
    expect(screen.getByText("公文类型")).toBeInTheDocument();
    expect(screen.getByText("结构大纲")).toBeInTheDocument();
  });

  it("pre-fills form fields when editing existing template", () => {
    render(
      <TemplateEditor
        open={true}
        template={existingTemplate}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />,
    );

    expect(screen.getByDisplayValue("编辑测试模板")).toBeInTheDocument();
    // Should show existing sections
    expect(screen.getByDisplayValue("标题段")).toBeInTheDocument();
    expect(screen.getByDisplayValue("正文段")).toBeInTheDocument();
  });

  it("adds a new section when + 添加段落 is clicked", async () => {
    const user = userEvent.setup();
    render(
      <TemplateEditor open={true} onSave={mockOnSave} onCancel={mockOnCancel} />,
    );

    // Default has 1 section; clicking adds another
    const addBtn = screen.getByText("+ 添加段落");
    await user.click(addBtn);

    // Should now have 2 section title inputs
    const titleInputs = screen.getAllByPlaceholderText("段落标题");
    expect(titleInputs.length).toBe(2);
  });

  it("removes a section when 删除段落 is clicked", async () => {
    const user = userEvent.setup();
    render(
      <TemplateEditor
        open={true}
        template={existingTemplate}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />,
    );

    // Starts with 2 sections
    expect(screen.getByDisplayValue("标题段")).toBeInTheDocument();
    expect(screen.getByDisplayValue("正文段")).toBeInTheDocument();

    // Click delete on the first section
    const deleteLinks = screen.getAllByText("删除段落");
    await user.click(deleteLinks[0]);

    // First section should be gone
    await waitFor(() => {
      expect(screen.queryByDisplayValue("标题段")).not.toBeInTheDocument();
    });
    // Second section should still be there
    expect(screen.getByDisplayValue("正文段")).toBeInTheDocument();
  });

  it("calls onCancel when 取消 button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <TemplateEditor open={true} onSave={mockOnSave} onCancel={mockOnCancel} />,
    );

    await user.click(screen.getByText("取 消"));
    expect(mockOnCancel).toHaveBeenCalledOnce();
  });

  it("renders writing points and format rules as tags in each section", () => {
    render(
      <TemplateEditor
        open={true}
        template={existingTemplate}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />,
    );

    // Writing points from first section
    expect(screen.getByText("简洁")).toBeInTheDocument();
    // Format rules from first section
    expect(screen.getByText("居中")).toBeInTheDocument();
    // Writing points from second section
    expect(screen.getByText("详细说明")).toBeInTheDocument();
  });
});
