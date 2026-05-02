import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import KnowledgeBase from "./pages/KnowledgeBase";
import Writing from "./pages/Writing";
import TemplateManager from "./pages/TemplateManager";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/knowledge-base" replace />} />
          <Route path="/knowledge-base" element={<KnowledgeBase />} />
          <Route path="/writing" element={<Writing />} />
          <Route path="/templates" element={<TemplateManager />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
