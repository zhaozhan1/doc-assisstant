import { useEffect, useState, useRef } from "react";
import { Card, Tag, Button, Segmented, Row, Col, Popconfirm, message, Modal } from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  RightOutlined,
} from "@ant-design/icons";
import { listTemplates, deleteTemplate, createTemplate, updateTemplate } from "../../api/templates";
import TemplateEditor from "./TemplateEditor";
import type { TemplateDef } from "../../types/api";

type FilterKey = "全部" | "内置模板" | "自定义模板";

const DOC_TYPE_ICONS: Record<string, string> = {
  notice: "📢",
  report: "📊",
  request: "📝",
  announcement: "📋",
  plan: "📄",
  other: "📃",
};

export default function TemplateManager() {
  const [templates, setTemplates] = useState<TemplateDef[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<FilterKey>("全部");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<
    TemplateDef | undefined
  >(undefined);
  const [detailTemplate, setDetailTemplate] = useState<TemplateDef | null>(
    null,
  );
  const fetchIdRef = useRef(0);

  const fetchTemplates = async () => {
    const fetchId = ++fetchIdRef.current;
    setLoading(true);
    try {
      const data = await listTemplates();
      if (fetchId === fetchIdRef.current) {
        setTemplates(data);
      }
    } catch {
      message.error("加载模板失败");
    } finally {
      if (fetchId === fetchIdRef.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchTemplates();
  }, []);

  const builtin = templates.filter((t) => t.is_builtin);
  const custom = templates.filter((t) => !t.is_builtin);

  const filteredBuiltin = filter === "自定义模板" ? [] : builtin;
  const filteredCustom = filter === "内置模板" ? [] : custom;

  const handleNewTemplate = () => {
    setEditingTemplate(undefined);
    setEditorOpen(true);
  };

  const handleEditTemplate = (tpl: TemplateDef) => {
    setEditingTemplate(tpl);
    setEditorOpen(true);
  };

  const handleDeleteTemplate = async (id: string) => {
    try {
      await deleteTemplate(id);
      message.success("删除成功");
      await fetchTemplates();
    } catch {
      message.error("删除失败");
    }
  };

  const handleSaveTemplate = async (
    data: Omit<TemplateDef, "id" | "is_builtin">,
  ) => {
    try {
      if (editingTemplate) {
        await updateTemplate(editingTemplate.id, {
          ...editingTemplate,
          ...data,
        });
        message.success("更新成功");
      } else {
        await createTemplate({
          id: "",
          is_builtin: false,
          ...data,
        } as TemplateDef);
        message.success("创建成功");
      }
      setEditorOpen(false);
      setEditingTemplate(undefined);
      await fetchTemplates();
    } catch {
      message.error("保存失败");
    }
  };

  const handleEditorCancel = () => {
    setEditorOpen(false);
    setEditingTemplate(undefined);
  };

  const sectionLabel = (count: number) => `${count} 个段落`;

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Segmented<FilterKey>
            options={["全部", "内置模板", "自定义模板"]}
            value={filter}
            onChange={setFilter}
          />
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleNewTemplate}>
            + 新建模板
          </Button>
        </Col>
      </Row>

      {filteredBuiltin.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h3 style={{ marginBottom: 16, color: "#374151" }}>
            内置模板（{filteredBuiltin.length}）
          </h3>
          <Row gutter={[16, 16]}>
            {filteredBuiltin.map((tpl) => (
              <Col key={tpl.id} xs={24} sm={12} md={8} lg={6}>
                <Card
                  hoverable
                  style={{ height: "100%" }}
                  styles={{ body: { padding: 20 } }}
                >
                  <div style={{ fontSize: 28, marginBottom: 8 }}>
                    {DOC_TYPE_ICONS[tpl.doc_type] ?? "📃"}
                  </div>
                  <Tag color="default" style={{ marginBottom: 8 }}>
                    内置
                  </Tag>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
                    {tpl.name}
                  </div>
                  <div style={{ color: "#9ca3af", fontSize: 13, marginBottom: 12 }}>
                    {sectionLabel(tpl.sections.length)}
                  </div>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => setDetailTemplate(tpl)}
                    style={{ padding: 0 }}
                  >
                    查看详情 <RightOutlined />
                  </Button>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      )}

      {filteredCustom.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h3 style={{ marginBottom: 16, color: "#374151" }}>
            自定义模板（{filteredCustom.length}）
          </h3>
          <Row gutter={[16, 16]}>
            {filteredCustom.map((tpl) => (
              <Col key={tpl.id} xs={24} sm={12} md={8} lg={6}>
                <Card
                  hoverable
                  style={{ height: "100%", borderStyle: "dashed" }}
                  styles={{ body: { padding: 20 } }}
                >
                  <div style={{ fontSize: 28, marginBottom: 8 }}>
                    {DOC_TYPE_ICONS[tpl.doc_type] ?? "📃"}
                  </div>
                  <Tag color="blue" style={{ marginBottom: 8 }}>
                    自定义
                  </Tag>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
                    {tpl.name}
                  </div>
                  <div style={{ color: "#9ca3af", fontSize: 13, marginBottom: 12 }}>
                    {sectionLabel(tpl.sections.length)}
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    <Button
                      type="link"
                      size="small"
                      onClick={() => setDetailTemplate(tpl)}
                    >
                      查看
                    </Button>
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleEditTemplate(tpl)}
                    >
                      编辑
                    </Button>
                    <Popconfirm
                      title="确定删除该模板吗？"
                      onConfirm={() => handleDeleteTemplate(tpl.id)}
                      okText="确 定"
                      cancelText="取 消"
                    >
                      <Button
                        type="link"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                      >
                        删除
                      </Button>
                    </Popconfirm>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      )}

      {!loading && filteredBuiltin.length === 0 && filteredCustom.length === 0 && (
        <div
          style={{ textAlign: "center", padding: "64px 0", color: "#9ca3af" }}
        >
          暂无模板
        </div>
      )}

      <TemplateEditor
        key={editingTemplate?.id ?? "new"}
        open={editorOpen}
        template={editingTemplate}
        onSave={handleSaveTemplate}
        onCancel={handleEditorCancel}
      />

      <Modal
        open={!!detailTemplate}
        title={detailTemplate?.name}
        onCancel={() => setDetailTemplate(null)}
        footer={null}
        width={560}
      >
        {detailTemplate && (
          <div style={{ marginTop: 8 }}>
            <p>
              <strong>公文类型：</strong>
              {detailTemplate.doc_type}
            </p>
            <p>
              <strong>段落结构：</strong>
            </p>
            {detailTemplate.sections.map((sec, idx) => (
              <Card key={idx} size="small" title={sec.title} style={{ marginBottom: 8 }}>
                {sec.writing_points.length > 0 && (
                  <div style={{ marginBottom: 4 }}>
                    <span style={{ color: "#6b7280", fontSize: 12 }}>
                      写作要点：
                    </span>{" "}
                    {sec.writing_points.map((wp, i) => (
                      <Tag key={i} color="blue">{wp}</Tag>
                    ))}
                  </div>
                )}
                {sec.format_rules.length > 0 && (
                  <div>
                    <span style={{ color: "#6b7280", fontSize: 12 }}>
                      格式规范：
                    </span>{" "}
                    {sec.format_rules.map((fr, i) => (
                      <Tag key={i} color="green">{fr}</Tag>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
