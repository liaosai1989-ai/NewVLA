# 本项目第三方依赖总览

依据仓库内 `**/pyproject.toml` 与源码实际调用整理：**PyPI 包**、**可选/运行时补充**、**外部二进制与服务**、**远端 API**。

**可能与实现不完全同步**：本文为维护性汇总，**可能有疏漏或滞后**。**权威优先级**：各子目录 `pyproject.toml`声明、源码中的 `import` / `subprocess` 调用与实际运行路径。**生产自检（如 `bootstrap doctor`）** 以 **`docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md`**（及最终实现）中对仓库的扫描结论为准，**非机械照抄**本表；二者冲突时先信 **源码与 spec**，再修本文。

---

## 1. Python 包（`pyproject.toml` 声明）

### `webhook/` — `webhook-cursor-executor`

| 包 | 用途（简述） |
|----|----------------|
| `fastapi` | HTTP Webhook 服务 |
| `uvicorn` | ASGI 服务进程 |
| `redis` | 连接 Redis |
| `rq` | 异步任务队列 |
| `pydantic` / `pydantic-settings` | 配置与数据模型 |
| `pycryptodome` | 飞书事件体 AES 解密 |
| `python-dotenv` | 加载执行工作区 `.env`（与 `ExecutorSettings` / 文件夹路由解析一致） |

**测试可选**：`pytest`、`fakeredis`、`httpx`。

### `onboard/` — `feishu-onboard`

| 包 | 用途 |
|----|------|
| `httpx` | 调用飞书开放平台 HTTP API |

**测试可选**：`pytest`、`pytest-httpx`。

### `dify_upload/` — `dify-upload`

| 包 | 用途 |
|----|------|
| `httpx` | 调用 Dify 数据集/文档 API |

**测试可选**：`pytest`。

### `feishu_fetch/` — `feishu-fetch`

- **主依赖列表为空**（仅标准库 + 子进程调 `lark-cli`）。
- **按文件类型可选**：`feishu_fetch` 对云空间 `drive_file` 若本地落盘后缀属于 **`MARKITDOWN_SUFFIXES`（与源码一致，共 7 类：`.doc`、`.docx`、`.ppt`、`.pptx`、`.xls`、`.xlsx`、`.pdf`）**，下载/导出后会 **`import markitdown`** 转成 Markdown 文本；**`.doc` 与 `.docx` 都要**，不是「只有 pdf」。未安装则报错。安装：同一 Python 环境 **`pip install markitdown`**（以下「建议安装」口吻指**不写进声明式 `dependencies`** 的包；**生产机 `bootstrap doctor` 自检见** `docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md` §5.1——该处已定 **自检必须可 import**。若业务只碰直读白名单格式，开发机可暂不装，`doctor` 行为以实现为准）。

### Markdown 相关说明

| 场景 | 是否额外 PyPI | 说明 |
|------|----------------|------|
| 仓库内文档、注入的 `task_prompt.md`、`rules` 下说明 | 否 | 由编辑器/Agent 当文本读，**无** `markdown` / `mistune` 等解析库依赖 |
| `feishu_fetch` 云文件 `.md` / `.markdown` | 否 | 与 `.txt` 等同属 **直读白名单**，原文读取，**不** 走 `markitdown` |
| `feishu_fetch` 将 **`.doc`/`.docx`/Office 套件/PDF** 转为 Markdown | 是（`markitdown`） | 后缀集合固定为上一段 7 类；飞书侧可能对旧 `.doc` 先导出为 `.docx`（见源码 `EXPORT_FORMATS`），最终仍走 `markitdown`。传递依赖由该包安装，不必在本仓重复列出 |
| `dify_upload` 上传内容 | 否 | 一般把字符串当分段/文档交给 Dify API，不做本地 Markdown AST 解析 |

---

## 2. 外部二进制 / 本地进程（非 PyPI）

| 名称 | 谁在用 | 说明 |
|------|--------|------|
| **Redis** | `webhook` | 去抖、状态、RQ 队列；URL 见 `REDIS_URL` |
| **`cursor`** | `webhook` | 固定命令名，需在 **PATH** 中；执行 `cursor agent --model …`（不经 `.env` 配可执行路径） |
| **`lark-cli`** | `feishu_fetch`、`onboard` | 固定命令名，需在 `PATH` 中；飞书文档/云空间操作与入轨后初始化 |

---

## 3. 远端服务 / API（凭据在根 `.env` 等）

| 服务 | 谁在用 | 说明 |
|------|--------|------|
| **飞书开放平台** | `onboard`（HTTP）、`feishu_fetch`（经 lark-cli） | 应用 ID/Secret、事件订阅、云文档/云空间等 |
| **Dify** | `dify_upload`、业务配置 | 控制台 API Base、API Key、`dataset_id` 等 |

---

## 4. 版本约束速查

- **webhook**：Python `>=3.12`
- **feishu_fetch**：Python `>=3.12`
- **dify_upload**：Python `>=3.11`
- **onboard**：Python `>=3.10`

各包具体版本区间以对应目录下 `pyproject.toml` 的 `dependencies` 为准。

---

## 5. 未纳入本文件的内容

- 本仓 **无** 根级 `package.json` / `requirements.txt`；按子包独立安装。
- **执行侧工作区** 内的 Cursor 技能、`lark-cli` 自带 Node/插件依赖等，属于工具链环境，非本仓库 `pyproject` 声明范围。
