import { useState } from "react";
import { Progress, Button, Card, Table, Collapse, Space, Statistic } from "antd";
import type { StatisticProps } from "antd";
import { CheckCircleFilled, CloseCircleFilled } from "@ant-design/icons";
import type { TaskProgress } from "../types/api";

interface ImportProgressProps {
  progress: TaskProgress;
  onCancel: () => void;
  onClose: () => void;
}

const successStyle: StatisticProps["styles"] = {
  content: { color: "#52c41a", fontSize: 16 },
};
const failStyle: StatisticProps["styles"] = {
  content: { color: "#ff4d4f", fontSize: 16 },
};
const skipStyle: StatisticProps["styles"] = {
  content: { color: "#8c8c8c", fontSize: 16 },
};

export function ImportProgress({
  progress,
  onCancel,
  onClose,
}: ImportProgressProps) {
  const [expanded, setExpanded] = useState(false);

  const percent =
    progress.total > 0
      ? Math.round((progress.processed / progress.total) * 100)
      : 0;

  if (progress.status === "running") {
    return (
      <Card style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 12 }}>
          <strong>正在导入...</strong>
          <span style={{ marginLeft: 8 }}>
            {progress.processed}/{progress.total}
          </span>
        </div>
        <Progress percent={percent} />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 12,
          }}
        >
          <Space size="large">
            <Statistic
              title="成功"
              value={progress.success}
              styles={successStyle}
              prefix={<CheckCircleFilled />}
            />
            <Statistic
              title="失败"
              value={progress.failed}
              styles={failStyle}
              prefix={<CloseCircleFilled />}
            />
            <Statistic
              title="跳过"
              value={progress.skipped}
              styles={skipStyle}
            />
          </Space>
          <Button danger onClick={onCancel}>
            取消
          </Button>
        </div>
      </Card>
    );
  }

  if (progress.status === "completed") {
    return (
      <Card
        style={{
          marginBottom: 16,
          borderLeft: "4px solid #52c41a",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <div>
            <CheckCircleFilled style={{ color: "#52c41a", marginRight: 8 }} />
            <strong>导入完成</strong>
            <span style={{ marginLeft: 8, color: "#666" }}>
              共处理 {progress.total} 个文件
            </span>
          </div>
          <Button size="small" onClick={onClose}>
            关闭
          </Button>
        </div>

        <Space
          size="large"
          style={{
            marginBottom: progress.failed_files.length > 0 ? 12 : 0,
          }}
        >
          <Statistic
            title="成功"
            value={progress.success}
            styles={successStyle}
            prefix={<CheckCircleFilled />}
          />
          <Statistic
            title="失败"
            value={progress.failed}
            styles={failStyle}
            prefix={<CloseCircleFilled />}
          />
          <Statistic
            title="跳过"
            value={progress.skipped}
            styles={skipStyle}
          />
        </Space>

        {progress.failed_files.length > 0 && (
          <Collapse
            ghost
            activeKey={expanded ? ["failures"] : []}
            onChange={() => setExpanded(!expanded)}
            items={[
              {
                key: "failures",
                label: `查看失败文件详情`,
                children: (
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={progress.failed_files.map((f, i) => ({
                      ...f,
                      key: i,
                    }))}
                    columns={[
                      { title: "文件名", dataIndex: "path", key: "path" },
                      {
                        title: "失败原因",
                        dataIndex: "error",
                        key: "error",
                      },
                      {
                        title: "操作",
                        key: "action",
                        render: () => (
                          <Button type="link" size="small">
                            重新索引
                          </Button>
                        ),
                      },
                    ]}
                  />
                ),
              },
            ]}
          />
        )}
      </Card>
    );
  }

  return null;
}
