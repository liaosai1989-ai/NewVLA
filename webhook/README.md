# webhook-cursor-executor

飞书 webhook -> Redis -> RQ -> Cursor CLI 执行器。

v1 范围：

- 飞书 challenge / 验签 / 解密
- Redis `event_seen` 幂等
- `document_id` 级 schedule / launch / finalize
- `.cursor_task/{run_id}` 注入目录
- spawn 前同步 Cursor CLI `maxMode`

## Local bootstrap

```powershell
cd c:\WorkPlace\NewVLA\webhook
uv venv .venv --python 3.13
uv pip install --python .\.venv\Scripts\python.exe -e .[test]
.\.venv\Scripts\python.exe -m pytest tests -v
```

## Runtime entrypoints

- HTTP app: `webhook_cursor_executor.app:build_app`
- RQ jobs:
- `webhook_cursor_executor.worker.schedule_document_job_entry`
- `webhook_cursor_executor.worker.launch_cursor_run_job_entry`
- `webhook_cursor_executor.worker.finalize_document_run_job_entry`
