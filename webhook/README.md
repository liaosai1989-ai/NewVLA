# webhook-cursor-executor

飞书 webhook -> Redis -> RQ -> Cursor CLI 执行器。

v1 范围：

- 飞书 challenge / 验签 / 解密
- Redis `event_seen` 幂等
- `document_id` 级 schedule / launch / finalize
- `.cursor_task/{run_id}` 注入目录
- spawn 前同步 Cursor CLI `maxMode`

**Cursor CLI 可执行文件：** 仅使用 PATH 上命令名 `cursor`（`shutil.which`）。根 `.env` 与**环境变量**均**勿**设已废弃的 `CURSOR_CLI_COMMAND`；自旧版升级须删除该键，否则无法加载配置。详见 `操作手册.md`（「自旧版升级」与排障表）。

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
