import { useEffect, useState, useCallback, useRef } from "react";
import {
  Card,
  Statistic,
  Tag,
  Upload,
  Select,
  DatePicker,
  Table,
  Button,
  Popconfirm,
  Space,
  Row,
  Col,
  message,
} from "antd";
import { InboxOutlined, FolderOpenOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useFileStore } from "../../stores/useFileStore";
import { useTaskStore } from "../../stores/useTaskStore";
import * as filesApi from "../../api/files";
import { ImportProgress } from "../../components/ImportProgress";
import type { IndexedFile, FileListParams } from "../../types/api";

const TAG_COLOR_MAP: Record<string, string> = {
  通知: "blue",
  报告: "green",
  方案: "orange",
  其他: "purple",
};

const DOC_TYPE_OPTIONS = ["通知", "报告", "方案", "其他"];

const SORT_OPTIONS: { label: string; value: string }[] = [
  { label: "最近更新", value: "doc_date_desc" },
  { label: "文件名", value: "file_name_asc" },
  { label: "分块数 ↓", value: "chunk_count_desc" },
];

const SORT_MAP: Record<
  string,
  { sort_by: FileListParams["sort_by"]; sort_order: "asc" | "desc" }
> = {
  doc_date_desc: { sort_by: "doc_date", sort_order: "desc" },
  doc_date_asc: { sort_by: "doc_date", sort_order: "asc" },
  file_name_asc: { sort_by: "file_name", sort_order: "asc" },
  file_name_desc: { sort_by: "file_name", sort_order: "desc" },
  chunk_count_desc: { sort_by: "chunk_count", sort_order: "desc" },
};

export default function KnowledgeBase() {
  const { files, stats, loading, error, fetchFiles, fetchStats, deleteFile } =
    useFileStore();
  const { taskId, progress, startUpload, reset } = useTaskStore();

  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[string, string] | undefined>(
    undefined,
  );
  const [sortValue, setSortValue] = useState("doc_date_desc");
  const submittedRef = useRef<Set<string>>(new Set());

  const getFileKey = (f: File) => `${f.name}:${f.size}:${f.lastModified}`;

  // Build query params from filters
  const buildParams = useCallback((): FileListParams => {
    const params: FileListParams = {};
    if (typeFilter) params.doc_types = typeFilter;
    if (dateRange) {
      params.date_from = dateRange[0];
      params.date_to = dateRange[1];
    }
    const sort = SORT_MAP[sortValue];
    if (sort) {
      params.sort_by = sort.sort_by;
      params.sort_order = sort.sort_order;
    }
    return params;
  }, [typeFilter, dateRange, sortValue]);

  // Fetch files on mount and when filters change
  useEffect(() => {
    fetchFiles(buildParams());
  }, [buildParams, fetchFiles]);

  // Fetch stats on mount
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Show store errors
  useEffect(() => {
    if (error) message.error(error);
  }, [error]);

  // Auto-refresh file list when import completes
  useEffect(() => {
    if (progress?.status === "completed") {
      fetchFiles(buildParams());
      fetchStats();
    }
  }, [progress?.status, buildParams, fetchFiles, fetchStats]);

  // Handle upload
  const handleUpload = async (uploadedFiles: File[]) => {
    if (uploadedFiles.length === 0) return;
    try {
      await startUpload(uploadedFiles);
    } catch {
      message.error("上传失败");
    }
  };

  // Handle delete
  const handleDelete = async (sourceFile: string) => {
    try {
      await deleteFile(sourceFile);
      fetchStats();
      message.success("删除成功");
    } catch {
      message.error("删除失败");
    }
  };

  // Handle reindex
  const handleReindex = async (sourceFile: string) => {
    try {
      await filesApi.reindexFile(sourceFile);
      fetchFiles(buildParams());
      message.success("重新索引成功");
    } catch {
      message.error("重新索引失败");
    }
  };

  // Handle classification change
  const handleClassificationChange = async (
    sourceFile: string,
    docType: string,
  ) => {
    try {
      await filesApi.updateClassification(sourceFile, docType);
      fetchFiles(buildParams());
      message.success("分类已更新");
    } catch {
      message.error("分类更新失败");
    }
  };

  // Close import result
  const handleCloseImport = () => {
    submittedRef.current.clear();
    reset();
    fetchFiles(buildParams());
    fetchStats();
  };

  // Table columns
  const columns: ColumnsType<IndexedFile> = [
    {
      title: "文件名",
      dataIndex: "file_name",
      key: "file_name",
      ellipsis: true,
    },
    {
      title: "类型",
      dataIndex: "doc_type",
      key: "doc_type",
      width: 100,
      render: (docType: string) => (
        <Tag color={TAG_COLOR_MAP[docType] || "default"}>{docType}</Tag>
      ),
    },
    {
      title: "日期",
      dataIndex: "doc_date",
      key: "doc_date",
      width: 120,
      render: (date: string | null) => date || "-",
    },
    {
      title: "分块数",
      dataIndex: "chunk_count",
      key: "chunk_count",
      width: 80,
    },
    {
      title: "操作",
      key: "action",
      width: 260,
      render: (_: unknown, record: IndexedFile) => (
        <Space size="small">
          <Popconfirm
            title="确定重新索引该文件吗？"
            onConfirm={() => handleReindex(record.source_file)}
            okText="确 定"
            cancelText="取 消"
          >
            <Button type="link" size="small">
              重新索引
            </Button>
          </Popconfirm>
          <Popconfirm
            title="确定删除该文件吗？"
            onConfirm={() => handleDelete(record.source_file)}
            okText="确 定"
            cancelText="取 消"
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
          <Select
            size="small"
            value={record.doc_type}
            style={{ width: 80 }}
            onChange={(value: string) =>
              handleClassificationChange(record.source_file, value)
            }
            options={DOC_TYPE_OPTIONS.map((t) => ({ label: t, value: t }))}
          />
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="总文件数" value={stats?.total_files ?? 0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="类型分布">
            <Space wrap>
              {stats?.type_distribution &&
                Object.entries(stats.type_distribution).map(([type, count]) => (
                  <Tag key={type} color={TAG_COLOR_MAP[type] || "default"}>
                    {type} {count}
                  </Tag>
                ))}
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="最后更新"
              value={
                stats?.last_updated
                  ? stats.last_updated.slice(0, 16).replace("T", " ")
                  : "-"
              }
            />
          </Card>
        </Col>
      </Row>

      {/* Upload Area */}
      <Space direction="vertical" style={{ width: "100%", marginBottom: 24 }}>
        <Upload.Dragger
          multiple
          showUploadList={false}
          beforeUpload={() => false}
          onChange={(info) => {
            const newFiles: File[] = [];
            for (const f of info.fileList) {
              if (!f.originFileObj) continue;
              const key = getFileKey(f.originFileObj);
              if (!submittedRef.current.has(key)) {
                submittedRef.current.add(key);
                newFiles.push(f.originFileObj);
              }
            }
            if (newFiles.length > 0) handleUpload(newFiles);
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            拖拽文件到此处，或点击选择文件
          </p>
        </Upload.Dragger>
        <Upload
          directory
          showUploadList={false}
          beforeUpload={() => false}
          onChange={(info) => {
            const newFiles: File[] = [];
            for (const f of info.fileList) {
              if (!f.originFileObj) continue;
              const key = getFileKey(f.originFileObj);
              if (!submittedRef.current.has(key)) {
                submittedRef.current.add(key);
                newFiles.push(f.originFileObj);
              }
            }
            if (newFiles.length > 0) handleUpload(newFiles);
          }}
        >
          <Button icon={<FolderOpenOutlined />} block>
            选择文件夹
          </Button>
        </Upload>
      </Space>

      {/* Import Progress / Result */}
      {taskId && progress && (
        <ImportProgress
          progress={progress}
          onCancel={() => {
            useTaskStore.getState().close();
            reset();
          }}
          onClose={handleCloseImport}
          onReindex={() =>
            message.info("请稍后在文件列表中重新索引该文件")
          }
        />
      )}

      {/* Filter Bar */}
      <Row gutter={16} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <Space>
            <span>类型：</span>
            <Select
              style={{ width: 120 }}
              value={typeFilter ?? "全部"}
              onChange={(value: string) =>
                setTypeFilter(value === "全部" ? undefined : value)
              }
              options={[
                { label: "全部", value: "全部" },
                ...DOC_TYPE_OPTIONS.map((t) => ({ label: t, value: t })),
              ]}
            />
          </Space>
        </Col>
        <Col>
          <DatePicker.RangePicker
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) {
                setDateRange([
                  dates[0].format("YYYY-MM-DD"),
                  dates[1].format("YYYY-MM-DD"),
                ]);
              } else {
                setDateRange(undefined);
              }
            }}
          />
        </Col>
        <Col flex="auto" style={{ textAlign: "right" }}>
          <Select
            style={{ width: 140 }}
            value={sortValue}
            onChange={setSortValue}
            options={SORT_OPTIONS}
          />
        </Col>
      </Row>

      {/* File Table */}
      <Table<IndexedFile>
        columns={columns}
        dataSource={files}
        rowKey="source_file"
        loading={loading}
        pagination={{
          showTotal: (total) => `共 ${total} 条`,
          showSizeChanger: true,
          defaultPageSize: 10,
        }}
      />
    </div>
  );
}
