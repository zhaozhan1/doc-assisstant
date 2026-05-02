import { useNavigate, useLocation } from "react-router-dom";
import { Layout as AntLayout, Menu } from "antd";
import {
  DatabaseOutlined,
  EditOutlined,
  FileTextOutlined,
  SettingOutlined,
} from "@ant-design/icons";

const { Sider, Content } = AntLayout;

const menuItems = [
  { key: "/knowledge-base", icon: <DatabaseOutlined />, label: "知识库" },
  { key: "/writing", icon: <EditOutlined />, label: "写作" },
  { key: "/templates", icon: <FileTextOutlined />, label: "模板管理" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider
        width={200}
        theme="light"
        style={{ borderRight: "1px solid #f0f0f0" }}
      >
        <div style={{ padding: "16px 20px", fontSize: 18, fontWeight: 700 }}>
          公文助手
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ border: "none" }}
        />
        <div
          style={{
            position: "absolute",
            bottom: 16,
            left: 20,
            fontSize: 12,
            color: "#999",
          }}
        >
          v0.1.0
        </div>
      </Sider>
      <AntLayout>
        <Content style={{ padding: 24, background: "#f5f5f5", minHeight: "auto" }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
