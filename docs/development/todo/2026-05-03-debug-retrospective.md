# 调试复盘与改进计划

**日期**: 2026-05-03
**关联分支**: `bugfix/settings-and-upload-fixes`
**问题**: .doc 导入不显示 + API key 不持久化，共经历 8 次迭代才定位

---

## 一、问题总结

| 问题 | 迭代次数 | 真正根因 |
|------|----------|----------|
| .doc 导入不显示 | 5 次 | PyInstaller 未打包 `docx/templates/`，textutil 产出无 styles 的 .docx 触发回退加载 |
| API key 不持久化 | 3 次 | `AppConfig()` 从 CWD 读 config.yaml（.app 中不存在），与 SettingsService 写入路径不一致 |

---

## 二、效率损失分析

### 2.1 日志丢失关键信息

structlog JSON renderer 将 Python traceback 序列化为字符串列表，**丢失完整调用栈**：

```json
"exc_info": ["<class 'FileNotFoundError'>", "FileNotFoundError(2, 'No such file or directory')", "<traceback object at 0x...>"]
```

这导致 3 次迭代看到相同的 `FileNotFoundError` 消息，每次都误判为 textutil 问题。

**如果第 1 次就能看到完整堆栈**（`docx/parts/styles.py:40 → _default_styles_xml → FileNotFoundError: default-styles.xml`），.doc 问题 1 轮即可解决。

### 2.2 未区分本地环境 vs .app 环境

在本地 `python3 -c "..."` 测试时：
- `docx/templates/` 在系统 Python site-packages 中，完整可用
- `get_data_dir()` 返回 `Path.cwd() / "doc-assistant"`，与 .app 不同
- CWD 即项目目录，可能存在开发用 config.yaml

每次"本地测试通过"都造成虚假信心，推迟了在 .app 内部添加诊断的决策。

### 2.3 修复症状而非追踪数据流

- .doc 问题：假设 `FileNotFoundError` = textutil 命令不存在，没追踪 textutil 成功后的下游失败
- API key 问题：假设是"保存时被覆盖"，没检查"启动时是否正确加载"这个上游环节

正确做法：从最终失败点向前逐层追踪，直到找到第一个产出错误数据的层。

---

## 三、改进措施

### 3.1 修复 traceback 序列化（代码改动）

在 `backend/app/main.py` 的 structlog 配置中，添加自定义处理器将 `exc_info` 格式化为完整堆栈字符串：

```python
# 在 shared_processors 中添加：
structlog.processors.format_exc_info,
```

这是 structlog 内置处理器，会将 `(type, value, traceback)` 元组转为完整堆栈文本，而非序列化后的占位符。

### 3.2 添加启动诊断日志（代码改动）

在 `_lifespan()` 中，启动后记录关键配置值（脱敏）：

```python
logger.info("配置加载完成: provider=%s, api_key_set=%s, base_url=%s",
            config.llm.default_provider,
            bool(config.llm.providers.get("openai", OpenAICompatibleConfig()).api_key),
            config.llm.providers.get("openai", OpenAICompatibleConfig()).base_url)
```

这样启动后就能一眼看出 API key 是否被正确加载。

### 3.3 建立 .app 环境验证清单（流程改进）

每次 PyInstaller 构建后，运行以下快速验证：

```bash
# 1. 确认关键数据文件存在
find dist/公文助手.app -name "default-styles.xml"    # docx 模板
find dist/公文助手.app -path "*/templates/*.yaml"     # 生成模板
find dist/公文助手.app -name "index.html"             # 前端入口

# 2. 确认配置路径一致
grep "resolve_path" backend/app/main.py               # 所有路径都走 resolve_path

# 3. 快速冒烟测试
open dist/公文助手.app && sleep 3
curl -s http://127.0.0.1:8000/api/settings/llm | python3 -m json.tool | grep api_key
# 应显示 "********" 而非空
```

### 3.4 Debug 前 5 分钟强制动作（流程改进）

遇到 .app 内 bug 时，**先做这 3 件事再提假设**：

1. **读日志获取完整异常** — 确认 traceback 可见，如果不可见则先修复日志
2. **在 .app 环境内验证假设** — 而非在本地 dev 环境验证
3. **从失败点向前追踪** — 列出数据经过的每一层，在哪一层首次出现错误值
