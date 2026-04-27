# feishu-fetch

最小可用的飞书正文抓取模块。凭证归 **onboard / 人工作初始化**；本包只读根 `.env` 中的 `FEISHU_REQUEST_TIMEOUT_SECONDS`、`FEISHU_APP_ID`（用于与 `lark-cli config show` 的 `appId` 比对），不通过子进程环境注入 `FEISHU_APP_SECRET`。

**Lark 子进程**：在代码中直接调用命令名 `lark-cli`（`PATH` 解析，与入轨一致），**不**经 `FeishuFetchSettings`、**不**经 `.env` 配置。若根 `.env` 仍含已废弃键 `LARK_CLI_COMMAND`，`load_feishu_fetch_settings` 会 **立刻报错**（`ValueError`），须删除该键后重试。

## 边界

- 只接收结构化 `FeishuFetchRequest`
- 不解析 webhook 事件
- 不从 URL 猜参数
- 不自动安装 `lark-cli`、不代替交互式登录
- 只支持 spec 明确列出的 v1 抓取路径

## 根 `.env` 与环境（合同）

| 键 | 含义 |
| --- | --- |
| `FEISHU_REQUEST_TIMEOUT_SECONDS` | 默认请求超时（秒，须为正数；可被 `FeishuFetchRequest.timeout_seconds` 覆盖） |
| `FEISHU_APP_ID` | 与 `lark config show` 中 `appId` 一致，用于预检 |
| `FEISHU_APP_SECRET` | **本模块不读取**（初始化仍由 `onboard` 或人工完成 `lark-cli config init`） |
| `FEISHU_FETCH_ENV_FILE` | 可选；可写在 **`cwd` 下 `.env`** 或设进程环境变量；须为**绝对路径**，指向管线工作区根下的 `.env`；**环境变量优先** |

**解析真源：**

- 若调用方显式传入 `load_feishu_fetch_settings(env_file=Path)` / `fetch_feishu_content(..., env_file=...)`，则使用该文件；
- 否则若进程环境变量 **`FEISHU_FETCH_ENV_FILE`** 有值，则使用该路径（优先于下面「指针」）；
- 否则若 **`Path.cwd() / ".env"`** 存在且其中含键 **`FEISHU_FETCH_ENV_FILE`**（须为**绝对路径**），则使用该路径指向的文件作为真源；
- 否则 `env_file = Path.cwd() / ".env"`，**约定此时进程 `cwd` 为工作区根**（与 `onboard` 中 `lark_config_init(cwd=...)` 的目录一致）。

**全部 lark 子进程**（`--help`、`config show`、各抓取子命令）在 `subprocess` 中均传 **`cwd=settings.workspace_root`**（即 `env_file` 的父目录）。

**第三方与 BUG-001：**

- **Lark 可执行文件**：固定 `lark-cli` + `shutil.which`；与 `onboard` 一致。
- **MarkItDown 等 Python 包**：在 `pyproject.toml` 声明，用正常 `import`；缺包时提示安装/venv，不引入 `MARKITDOWN_COMMAND` 或硬编码可执行文件路径。合并前在包内对 `subprocess` / `*_COMMAND` 等做自检，见 `BugList.md` **BUG-001**。

## 目录

```text
feishu_fetch/
├─ src/feishu_fetch/
│  ├─ __init__.py
│  ├─ config.py      # 设置加载
│  ├─ lark_env.py    # config show JSON
│  ├─ errors.py
│  ├─ models.py
│  └─ facade.py
└─ tests/
```

## 依赖前提

- 运行前能在 `workspace_root` 下通过 `PATH` 执行 `lark-cli`
- 已完成 `lark-cli config` 且 `appId` 与根 `.env` 的 `FEISHU_APP_ID` 一致
- 命中 Office/PDF 等转换路径时依赖 **MarkItDown**（`import markitdown`），不通过额外 CLI 名配置

## 支持的 lark 子命令（与 CLI 主版本）

本包固定调用与下列一致的子流程（**建议你与维护仓固定次版本在 CI/手测中验证**）：

- 预检：`lark-cli --help`、`lark-cli config show`
- `cloud_docx`：`docs +fetch`（`--api-version v2` 等，见 `facade.py`）
- `drive_file`：`drive +download` / `+export` / `+task_result` / `+export-download`

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

# 在管线工作区根下执行，或设 FEISHU_FETCH_ENV_FILE=绝对路径\.env
result = fetch_feishu_content(request)
print(result.artifact_path)
```

## 支持范围

- `cloud_docx`
  - 固定调用 `lark` 的 `docs +fetch`（见代码）
  - 从 `data.document.content` 提取正文
  - 落盘为 UTF-8 文本文件
- `drive_file`
  - `file` 走 `drive +download`
  - `doc` / `docx` 固定导出为 `.docx`
  - `sheet` 固定导出为 `.xlsx`
  - 直读格式保留原文件
  - 需转换格式用 MarkItDown 转成 Markdown

## 测试

**L0（默认 CI）：**

```powershell
Set-Location "c:\Cursor WorkSpace\NewVLA\feishu_fetch"
python -m pytest tests -v
```

**L1（真云，默认跳过）：** 设 `FEISHU_FETCH_L1_RUN=1` 并配好 `document_id` / 凭证后，可跑 `tests/test_cloud_docx_integration_l1.py` 中占位用例；见该文件与 `pyproject.toml` 中 `l1_cloud` 标记。CI 默认不跑 L1（勿在未接真断言前在主干上开 RUN 让 CI 红）。
