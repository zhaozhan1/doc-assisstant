import { useState } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Tag,
  Space,
  Divider,
} from "antd";
import { PlusOutlined, MinusCircleOutlined } from "@ant-design/icons";
import type { TemplateDef, TemplateSection } from "../../types/api";

const DOC_TYPE_OPTIONS = [
  { label: "通知", value: "notice" },
  { label: "报告", value: "report" },
  { label: "请示", value: "request" },
  { label: "公告", value: "announcement" },
  { label: "方案", value: "plan" },
  { label: "其他", value: "other" },
];

interface TemplateEditorProps {
  open: boolean;
  template?: TemplateDef;
  onSave: (data: Omit<TemplateDef, "id" | "is_builtin">) => void;
  onCancel: () => void;
}

function defaultSection(): TemplateSection {
  return {
    title: "",
    writing_points: [],
    format_rules: [],
  };
}

function templateToSections(template?: TemplateDef): TemplateSection[] {
  if (!template || template.sections.length === 0) {
    return [defaultSection()];
  }
  return template.sections.map((s) => ({
    title: s.title,
    writing_points: [...s.writing_points],
    format_rules: [...s.format_rules],
  }));
}

export default function TemplateEditor({
  open,
  template,
  onSave,
  onCancel,
}: TemplateEditorProps) {
  const [sections, setSections] = useState<TemplateSection[]>(
    templateToSections(template),
  );
  const [name, setName] = useState(template?.name ?? "");
  const [docType, setDocType] = useState(template?.doc_type ?? "notice");

  const handleAddSection = () => {
    setSections((prev) => [...prev, defaultSection()]);
  };

  const handleRemoveSection = (index: number) => {
    setSections((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSectionTitleChange = (index: number, value: string) => {
    setSections((prev) =>
      prev.map((s, i) => (i === index ? { ...s, title: value } : s)),
    );
  };

  const handleAddTag = (
    index: number,
    field: "writing_points" | "format_rules",
    value: string,
  ) => {
    if (!value.trim()) return;
    setSections((prev) =>
      prev.map((s, i) =>
        i === index ? { ...s, [field]: [...s[field], value.trim()] } : s,
      ),
    );
  };

  const handleRemoveTag = (
    index: number,
    field: "writing_points" | "format_rules",
    tagIndex: number,
  ) => {
    setSections((prev) =>
      prev.map((s, i) =>
        i === index
          ? { ...s, [field]: s[field].filter((_, ti) => ti !== tagIndex) }
          : s,
      ),
    );
  };

  const handleSave = () => {
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      doc_type: docType,
      sections: sections.filter((s) => s.title.trim()),
    });
  };

  const isEditing = !!template;
  const title = isEditing ? "编辑模板" : "新建模板";

  return (
    <Modal
      open={open}
      title={title}
      onCancel={onCancel}
      width={640}
      footer={
        <Space>
          <Button onClick={onCancel}>取 消</Button>
          <Button type="primary" onClick={handleSave}>
            保存
          </Button>
        </Space>
      }
      destroyOnHidden
    >
      <Form layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item label="模板名称" required>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="输入模板名称"
          />
        </Form.Item>

        <Form.Item label="公文类型">
          <Select
            value={docType}
            onChange={setDocType}
            options={DOC_TYPE_OPTIONS}
            style={{ width: "100%" }}
          />
        </Form.Item>

        <Divider titlePlacement="left">结构大纲</Divider>

        {sections.map((section, idx) => (
          <div
            key={idx}
            style={{
              marginBottom: 16,
              padding: 12,
              border: "1px solid #f0f0f0",
              borderRadius: 6,
            }}
          >
            <Form.Item label="段落标题" style={{ marginBottom: 8 }}>
              <Input
                value={section.title}
                onChange={(e) =>
                  handleSectionTitleChange(idx, e.target.value)
                }
                placeholder="段落标题"
              />
            </Form.Item>

            <Form.Item label="写作要点" style={{ marginBottom: 8 }}>
              <TagInput
                tags={section.writing_points}
                onAdd={(val) => handleAddTag(idx, "writing_points", val)}
                onRemove={(tagIdx) =>
                  handleRemoveTag(idx, "writing_points", tagIdx)
                }
                placeholder="添加写作要点"
              />
            </Form.Item>

            <Form.Item label="格式规范" style={{ marginBottom: 0 }}>
              <TagInput
                tags={section.format_rules}
                onAdd={(val) => handleAddTag(idx, "format_rules", val)}
                onRemove={(tagIdx) =>
                  handleRemoveTag(idx, "format_rules", tagIdx)
                }
                placeholder="添加格式规范"
              />
            </Form.Item>

            <Button
              type="link"
              danger
              icon={<MinusCircleOutlined />}
              onClick={() => handleRemoveSection(idx)}
              style={{ padding: 0, marginTop: 8 }}
            >
              删除段落
            </Button>
          </div>
        ))}

        <Button
          type="dashed"
          onClick={handleAddSection}
          icon={<PlusOutlined />}
          style={{ width: "100%" }}
        >
          + 添加段落
        </Button>
      </Form>
    </Modal>
  );
}

// ---- TagInput sub-component ----
interface TagInputProps {
  tags: string[];
  onAdd: (value: string) => void;
  onRemove: (index: number) => void;
  placeholder?: string;
}

function TagInput({ tags, onAdd, onRemove, placeholder }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleConfirm = () => {
    if (inputValue.trim()) {
      onAdd(inputValue.trim());
      setInputValue("");
    }
  };

  return (
    <div>
      <Space wrap style={{ marginBottom: 4 }}>
        {tags.map((tag, idx) => (
          <Tag key={idx} closable onClose={() => onRemove(idx)}>
            {tag}
          </Tag>
        ))}
      </Space>
      <Input
        size="small"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onPressEnter={handleConfirm}
        onBlur={handleConfirm}
        placeholder={placeholder}
        style={{ width: 160 }}
      />
    </div>
  );
}
