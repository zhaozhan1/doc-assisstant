# TODO: 迁移 .doc/.ppt 提取方案为纯 Python 实现

**创建日期**: 2026-05-03
**优先级**: 低（仅当迁移到非 macOS 环境时需要）
**相关文件**: `backend/app/ingestion/extractor.py`（`_extract_doc`、`_extract_ppt` 方法）

## 现状

`.doc`（Word 97-2003）和 `.ppt`（PowerPoint 97-2003）是 OLE2 二进制格式，目前依赖 macOS 内置 `textutil` 命令做格式转换：

- `.doc` → `textutil -convert docx` → 复用 `_extract_docx`
- `.ppt` → `textutil -convert txt` → 复用 `_extract_txt`
- `.xls` 已使用纯 Python 库 `xlrd`，无需修改

## 触发条件

当应用部署到 Linux / Windows 或 macOS 环境缺少 `textutil` 时，`.doc` 和 `.ppt` 文件导入将失败。

## 候选方案

| 库 | .doc | .ppt | 纯 Python | 备注 |
|---|---|---|---|---|
| [sharepoint-to-text](https://github.com/Horsmann/sharepoint-to-text) | ✅ | ✅ | ✅ | 统一 API，Apache 2.0，项目较新(2024) |
| [pyxtxt](https://pypi.org/project/pyxtxt/) | ✅ | ✅ | ✅ | 轻量，文档极少 |
| [olefile](https://github.com/decalage2/olefile) + 自行解析 | 部分 | 部分 | ✅ | 成熟但需自行实现 Word/PowerPoint 流解析 |
| Apache Tika (需 JRE) | ✅ | ✅ | ❌ | 最全面，依赖 Java |
| LibreOffice headless | ✅ | ✅ | ❌ | 需安装 LibreOffice |

## 实施指引

1. 在 `_extract_doc` / `_extract_ppt` 中检测 `textutil` 是否可用
2. 不可用时 fallback 到纯 Python 库（推荐 `sharepoint-to-text` 或 `olefile`）
3. 或直接替换为纯 Python 库，消除平台依赖
