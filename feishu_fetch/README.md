# feishu-fetch

最小可用的飞书正文抓取模块。

## 边界

- 只接收结构化 `FeishuFetchRequest`
- 不解析 webhook 事件
- 不从 URL 猜参数
- 不自动安装 `lark-cli`
- 不自动修复登录态
- 只支持 spec 明确列出的 v1 抓取路径

## 目录

```text
feishu_fetch/
├─ src/feishu_fetch/
│  ├─ __init__.py
│  ├─ errors.py
│  ├─ models.py
│  └─ facade.py
└─ tests/
```

## 依赖前提

- 运行 `cloud_docx` 或 `drive_file` 前，环境里必须能直接执行 `lark-cli`
- 只有命中 `.doc`、`.docx`、`.ppt`、`.pptx`、`.xls`、`.xlsx`、`.pdf` 转换路径时，才需要 `MarkItDown`
- 模块只检测依赖，不负责自动安装

## 使用方式

```python
from pathlib import Path

from feishu_fetch import FeishuFetchRequest, fetch_feishu_content

request = FeishuFetchRequest(
    ingest_kind="cloud_docx",
    document_id="doccnxxxx",
    output_dir=Path(".cursor_task/run_001/outputs/feishu_fetch"),
    title_hint="weekly-sync",
)

result = fetch_feishu_content(request)
print(result.artifact_path)
```

## 支持范围

- `cloud_docx`
  - 固定调用 `lark-cli docs +fetch`
  - 从 `data.document.content` 提取正文
  - 落盘为 UTF-8 文本文件
- `drive_file`
  - `file` 走 `drive +download`
  - `doc` / `docx` 固定导出为 `.docx`
  - `sheet` 固定导出为 `.xlsx`
  - 直读格式保留原文件
  - 需转换格式转成 Markdown

## 测试

```powershell
cd c:\WorkPlace\NewVLA\feishu_fetch
.\.venv\Scripts\python.exe -m pytest tests -v
```
