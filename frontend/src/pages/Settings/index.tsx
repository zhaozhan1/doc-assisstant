import { useEffect, useState } from "react";
import {
  Card,
  Tabs,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Space,
  Alert,
  Modal,
  List,
  message,
} from "antd";
import {
  FolderOpenOutlined,
  FileOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import { useSettingsStore } from "../../stores/useSettingsStore";
import type { BrowseResult } from "../../types/api";

export default function Settings() {
  const {
    kb,
    llm,
    generation,
    onlineSearch,
    loading,
    error,
    fetchAllConfigs,
    updateKB,
    updateLLM,
    updateGeneration,
    updateOnlineSearch,
    testConnection,
    browseDirectory,
  } = useSettingsStore();

  const [activeTab, setActiveTab] = useState("kb");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [browseData, setBrowseData] = useState<BrowseResult | null>(null);
  const [browseLoading, setBrowseLoading] = useState(false);
  const [browseTarget, setBrowseTarget] = useState<{
    form: "kb" | "generation";
    field: string;
  } | null>(null);

  // Forms
  const [kbForm] = Form.useForm();
  const [llmForm] = Form.useForm();
  const [generationForm] = Form.useForm();
  const [onlineSearchForm] = Form.useForm();

  useEffect(() => {
    fetchAllConfigs();
  }, [fetchAllConfigs]);

  // Sync store data to forms
  useEffect(() => {
    if (kb) kbForm.setFieldsValue(kb);
  }, [kb, kbForm]);

  useEffect(() => {
    if (llm) llmForm.setFieldsValue(llm);
  }, [llm, llmForm]);

  useEffect(() => {
    if (generation) generationForm.setFieldsValue(generation);
  }, [generation, generationForm]);

  useEffect(() => {
    if (onlineSearch) onlineSearchForm.setFieldsValue(onlineSearch);
  }, [onlineSearch, onlineSearchForm]);

  // Browse directory
  const handleBrowse = async (
    form: "kb" | "generation",
    field: string,
    currentPath?: string,
  ) => {
    setBrowseTarget({ form, field });
    setBrowseOpen(true);
    setBrowseLoading(true);
    try {
      const result = await browseDirectory(currentPath || ".");
      setBrowseData(result);
    } catch {
      message.error("浏览目录失败");
    } finally {
      setBrowseLoading(false);
    }
  };

  const handleBrowseDirClick = async (path: string) => {
    setBrowseLoading(true);
    try {
      const result = await browseDirectory(path);
      setBrowseData(result);
    } catch {
      message.error("浏览目录失败");
    } finally {
      setBrowseLoading(false);
    }
  };

  const handleBrowseSelect = (path: string) => {
    if (!browseTarget) return;
    const targetForm =
      browseTarget.form === "kb" ? kbForm : generationForm;
    targetForm.setFieldValue(browseTarget.field, path);
    setBrowseOpen(false);
  };

  // Test connection
  const handleTestConnection = async () => {
    const values = onlineSearchForm.getFieldsValue();
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testConnection(values);
      setTestResult(result);
    } catch {
      setTestResult({ success: false, message: "连接测试失败" });
    } finally {
      setTesting(false);
    }
  };

  // Save handlers
  const handleSaveKB = async () => {
    try {
      const values = await kbForm.validateFields();
      await updateKB(values);
      message.success("知识库配置已保存");
    } catch {
      // validation error
    }
  };

  const handleSaveLLM = async () => {
    try {
      const values = await llmForm.validateFields();
      await updateLLM(values);
      message.success("LLM 配置已保存");
    } catch {
      // validation error
    }
  };

  const handleSaveGeneration = async () => {
    try {
      const values = await generationForm.validateFields();
      await updateGeneration(values);
      message.success("输出配置已保存");
    } catch {
      // validation error
    }
  };

  const handleSaveOnlineSearch = async () => {
    try {
      const values = await onlineSearchForm.validateFields();
      await updateOnlineSearch(values);
      message.success("在线检索配置已保存");
    } catch {
      // validation error
    }
  };

  const tabItems = [
    {
      key: "kb",
      label: "知识库",
      children: (
        <Form form={kbForm} layout="vertical" disabled={loading}>
          <Form.Item label="源文件夹路径" name="source_folder">
            <Input
              addonAfter={
                <Button
                  type="text"
                  size="small"
                  icon={<FolderOpenOutlined />}
                  onClick={() => handleBrowse("kb", "source_folder")}
                >
                  浏览
                </Button>
              }
            />
          </Form.Item>
          <Form.Item label="数据库路径" name="db_path">
            <Input />
          </Form.Item>
          <Form.Item label="分块大小（字）" name="chunk_size">
            <InputNumber min={100} max={2000} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="分块重叠（字）" name="chunk_overlap">
            <InputNumber min={0} max={500} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleSaveKB}>
              保存
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: "llm",
      label: "LLM",
      children: (
        <Form form={llmForm} layout="vertical" disabled={loading}>
          <Form.Item label="聊天提供商" name="default_provider">
            <Select
              options={[
                { label: "OpenAI 兼容", value: "openai" },
                { label: "Ollama", value: "ollama" },
                { label: "Claude", value: "claude" },
              ]}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate>
            {() => {
              const provider = llmForm.getFieldValue("default_provider");
              if (provider === "openai") {
                return (
                  <>
                    <Form.Item label="Base URL" name="openai_base_url">
                      <Input />
                    </Form.Item>
                    <Form.Item label="API Key" name="openai_api_key">
                      <Input.Password />
                    </Form.Item>
                    <Form.Item label="Chat Model" name="openai_chat_model">
                      <Input />
                    </Form.Item>
                  </>
                );
              }
              if (provider === "ollama") {
                return (
                  <>
                    <Form.Item label="Base URL" name="ollama_base_url">
                      <Input />
                    </Form.Item>
                    <Form.Item label="Chat Model" name="ollama_chat_model">
                      <Input />
                    </Form.Item>
                  </>
                );
              }
              if (provider === "claude") {
                return (
                  <>
                    <Form.Item label="Base URL" name="claude_base_url">
                      <Input />
                    </Form.Item>
                    <Form.Item label="API Key" name="claude_api_key">
                      <Input.Password />
                    </Form.Item>
                    <Form.Item label="Chat Model" name="claude_chat_model">
                      <Input />
                    </Form.Item>
                  </>
                );
              }
              return null;
            }}
          </Form.Item>
          <Form.Item label="Embedding 提供商" name="embed_provider">
            <Select
              options={[
                { label: "OpenAI 兼容", value: "openai" },
                { label: "Ollama", value: "ollama" },
              ]}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate>
            {() => {
              const embedProv = llmForm.getFieldValue("embed_provider");
              if (embedProv === "openai") {
                return (
                  <Form.Item label="Embed Model (OpenAI)" name="openai_embed_model">
                    <Input />
                  </Form.Item>
                );
              }
              if (embedProv === "ollama") {
                return (
                  <Form.Item label="Embed Model (Ollama)" name="ollama_embed_model">
                    <Input />
                  </Form.Item>
                );
              }
              return null;
            }}
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleSaveLLM}>
              保存
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: "onlineSearch",
      label: "在线检索",
      children: (
        <Form form={onlineSearchForm} layout="vertical" disabled={loading}>
          <Form.Item
            label="启用在线检索"
            name="enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item label="搜索提供商" name="provider">
            <Select
              options={[
                { label: "百度", value: "baidu" },
              ]}
            />
          </Form.Item>
          <Form.Item label="API Key" name="api_key">
            <Input.Password />
          </Form.Item>
          <Form.Item label="Base URL" name="base_url">
            <Input />
          </Form.Item>
          <Form.Item label="搜索域名限制" name="domains">
            <Select mode="tags" placeholder="输入域名后回车" />
          </Form.Item>
          <Form.Item label="最大结果数" name="max_results">
            <InputNumber min={1} max={20} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" onClick={handleSaveOnlineSearch}>
                保存
              </Button>
              <Button onClick={handleTestConnection} loading={testing}>
                测试连接
              </Button>
            </Space>
          </Form.Item>
          {testResult && (
            <Alert
              type={testResult.success ? "success" : "error"}
              message={testResult.message}
              showIcon
              style={{ marginTop: 8 }}
            />
          )}
        </Form>
      ),
    },
    {
      key: "generation",
      label: "输出",
      children: (
        <Form form={generationForm} layout="vertical" disabled={loading}>
          <Form.Item label="输出格式" name="output_format">
            <Select
              options={[{ label: "Word (.docx)", value: "docx" }]}
            />
          </Form.Item>
          <Form.Item label="保存路径" name="save_path">
            <Input
              addonAfter={
                <Button
                  type="text"
                  size="small"
                  icon={<FolderOpenOutlined />}
                  onClick={() => handleBrowse("generation", "save_path")}
                >
                  浏览
                </Button>
              }
            />
          </Form.Item>
          <Form.Item
            label="包含来源引用"
            name="include_sources"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item label="Word 模板路径" name="word_template_path">
            <Input
              addonAfter={
                <Button
                  type="text"
                  size="small"
                  icon={<FileOutlined />}
                  onClick={() =>
                    handleBrowse("generation", "word_template_path")
                  }
                >
                  浏览
                </Button>
              }
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleSaveGeneration}>
              保存
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 640, margin: "0 auto" }}>
      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      <Modal
        title="选择目录"
        open={browseOpen}
        onCancel={() => setBrowseOpen(false)}
        footer={null}
        width={480}
      >
        {browseLoading ? (
          <div style={{ textAlign: "center", padding: 24 }}>
            <LoadingOutlined style={{ fontSize: 24 }} />
          </div>
        ) : (
          browseData && (
            <div>
              <Button
                type="link"
                size="small"
                onClick={() => handleBrowseSelect(browseData.path)}
                style={{ marginBottom: 8 }}
              >
                选择当前目录: {browseData.path}
              </Button>
              <List
                size="small"
                dataSource={browseData.children}
                renderItem={(item) => (
                  <List.Item
                    actions={
                      item.is_dir
                        ? [
                            <Button
                              key="open"
                              type="link"
                              size="small"
                              onClick={() => handleBrowseDirClick(item.path)}
                            >
                              打开
                            </Button>,
                          ]
                        : []
                    }
                  >
                    <List.Item.Meta
                      avatar={
                        item.is_dir ? (
                          <FolderOpenOutlined />
                        ) : (
                          <FileOutlined />
                        )
                      }
                      title={item.name}
                      description={item.path}
                    />
                    {item.is_dir && (
                      <Button
                        type="link"
                        size="small"
                        onClick={() => handleBrowseSelect(item.path)}
                      >
                        选择
                      </Button>
                    )}
                  </List.Item>
                )}
              />
            </div>
          )
        )}
      </Modal>
    </div>
  );
}
