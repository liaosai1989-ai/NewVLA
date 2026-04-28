# webhook-cursor-executor

飞书 webhook -> Redis -> RQ -> Cursor CLI 执行器。

v1 范围：

- 飞书 challenge / 验签 / 解密
- Redis `event_seen` 幂等
- `document_id` 级 schedule / launch / finalize
- `.cursor_task/{run_id}` 注入目录
- spawn 前同步 Cursor CLI `maxMode`

**Cursor CLI 可执行文件：** 仅使用 PATH 上命令名 `cursor`（`shutil.which`）。根 `.env` 与**环境变量**均**勿**设已废弃的 `CURSOR_CLI_COMMAND`；自旧版升级须删除该键，否则无法加载配置。详见 `操作手册.md`（「自旧版升级」与排障表）。

## 执行工作区内嵌路径（生产签字）

bootstrap **`materialize-workspace`**（见仓库根 **`bootstrap/README.md`**）后，**运行时 webhook 包根**落在 **`{WORKSPACE_ROOT}/runtime/webhook`**，与克隆根旁的 **`webhook/`** 目录同源但**以工作区拷贝为准**（**`pip install -e .`** 的 **`cwd`** = **`runtime/webhook`**，`VLA_WORKSPACE_ROOT` = 工作区根）。

- **`GET /health`**：FastAPI JSON 探活；完整人机签字须在进程已监听后用 **`bootstrap probe`** **全量段**命中 **`GET {WEBHOOK_PROBE_BASE}/health`**（**`WEBHOOK_PROBE_BASE`** 见 **`docs/superpowers/samples/pipeline-workspace-root.env.example`**）。
- **`bootstrap probe`**：**`doctor --workspace`** 之后可先 **`bootstrap probe --no-http`**；Redis / webhook（及按需 RQ）已监听后再 **`bootstrap probe`** 全量（不传 **`--no-http`**）。细则与退出码见 **`bootstrap/README.md`**（**`install-workspace-editables`**、探活分段）。

以下为**维护仓开发**时在克隆根 **`webhook/`** 本地的安装示例；路径一律换成本机 **`{WORKSPACE_ROOT}/runtime/webhook`** 再谈生产等价。

## Local bootstrap

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
