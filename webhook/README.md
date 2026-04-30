# webhook-cursor-executor

飞书 webhook -> Redis -> RQ -> Cursor CLI 执行器。

v1 范围：

- 飞书 challenge / 验签 / 解密
- Redis `event_seen` 幂等
- `document_id` 级 schedule / launch / finalize
- `.cursor_task/{run_id}` 注入目录
- spawn 前同步 Cursor CLI `maxMode`

**Cursor Agent CLI：** 子进程使用 PATH 上命令名 **`agent`**（`shutil.which`），以 **`agent -p --force --trust --workspace … --model …`** 非交互执行；**不是** 桌面应用启动器 **`cursor`**（Electron 会吞掉参数并假成功、无产物）。根 `.env` 与**环境变量**均**勿**设已废弃的 `CURSOR_CLI_COMMAND`。详见 `操作手册.md`。

## 执行工作区内嵌路径（生产签字）

bootstrap **`materialize-workspace`**（见仓库根 **`bootstrap/README.md`**）后，**运行时 webhook 包根**落在 **`{WORKSPACE_ROOT}/runtime/webhook`**，与克隆根旁的 **`webhook/`** 目录同源但**以工作区拷贝为准**（**`pip install -e .`** 的 **`cwd`** = **`runtime/webhook`**，`VLA_WORKSPACE_ROOT` = 工作区根）。

- **`GET /health`**：FastAPI JSON 探活；完整人机签字须在进程已监听后用 **`bootstrap probe`** **全量段**命中 **`GET {WEBHOOK_PROBE_BASE}/health`**（**`WEBHOOK_PROBE_BASE`** 见 **`docs/superpowers/samples/pipeline-workspace-root.env.example`**）。
- **`bootstrap probe`**：**`doctor --workspace`** 之后可先 **`bootstrap probe --no-http`**；Redis / webhook（及按需 RQ）已监听后再 **`bootstrap probe`** 全量（不传 **`--no-http`**）。细则与退出码见 **`bootstrap/README.md`**（**`install-workspace-editables`**、探活分段）。

以下为**维护仓开发**时在克隆根 **`webhook/`** 本地的安装示例；路径一律换成本机 **`{WORKSPACE_ROOT}/runtime/webhook`** 再谈生产等价。

> **`.venv` 适用范围：** 下述 **`uv venv` / `.\.venv\Scripts\...` 仅用于维护仓库克隆根** 本地调试、单测、可编辑安装隔离；详见 **`.cursor/rules/anti-venv.mdc`**。**物化后的执行工作区（`VLA_WORKSPACE_ROOT`）与生产 7×24**：**禁止** 把工作区内 `.venv`（例如 `runtime/webhook/.venv`）当作 Webhook、RQ 的 **正式运行时**；须 **`py -3.12`**（或容器/镜像内固定解释器）+ **`bootstrap install-workspace-editables`** 或平台等价安装，**禁止** 把「激活工作区 `.venv` 再启动」写进正式运维 SOP。

## Local bootstrap（仅维护仓调试）

```powershell
cd c:\WorkPlace\NewVLA\webhook
uv venv .venv --python 3.12
uv pip install --python .\.venv\Scripts\python.exe -e .[test]
.\.venv\Scripts\python.exe -m pytest tests -v
```

## Runtime entrypoints

- HTTP app: `webhook_cursor_executor.app:build_app`
- RQ jobs:
- `webhook_cursor_executor.worker.schedule_document_job_entry`
- `webhook_cursor_executor.worker.launch_cursor_run_job_entry`
- `webhook_cursor_executor.worker.finalize_document_run_job_entry`
