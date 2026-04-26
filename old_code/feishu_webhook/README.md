# feishu_webhook

从原 VLA 仓库剥离出的“飞书 Webhook -> Redis 去重/去抖 -> RQ 入队”模块。

## 目录职责

- `webhook_app.py`
  - FastAPI 入口
  - 飞书 challenge
  - 签名校验 / 解密
  - 事件解析
  - Redis 幂等
  - Redis 去抖
  - RQ 入队
- `queue_rq.py`
  - RQ 队列适配器
  - 双 Redis 连接构造
- `worker_tasks.py`
  - RQ 任务入口
  - debounce flush 任务
  - 主任务回调分发
- `settings.py`
  - Webhook 最小配置集
- `crypto.py`
  - 飞书签名与 AES 解密
- `events.py`
  - 从事件体提取 `document_id / ingest_kind / file_type_hint`
- `types.py`
  - `FeishuIngestKind` 及相关转换
- `webhook_debounce.py`
  - 按 `document_id` 去抖的 Redis 快照 / claim / 延迟入队逻辑

## 依赖

最少依赖：

```bash
pip install fastapi redis rq uvicorn pycryptodome pydantic pydantic-settings
```

## 双 Redis 连接

这个模块要求把“状态 Redis”和“RQ Redis”分开初始化。

- `state_redis`
  - `Redis.from_url(settings.redis_url, decode_responses=True)`
  - 用于：
    - `event_id + document_id` 去重
    - debounce 快照
    - docx 自动订阅去重键
    - `/health`
- `rq_redis`
  - `Redis.from_url(settings.redis_url)`
  - 用于：
    - `rq.Queue(...)`
    - `enqueue(...)`
    - `enqueue_in(...)`

## Webhook 处理流程

1. 接收飞书 POST
2. 先处理 `url_verification`
3. 校验签名
4. 解密或解析 body
5. 用 `extract_feishu_ingest(...)` 提取：
   - `document_id`
   - `feishu_ingest_kind`
   - `feishu_file_type_hint`
6. 用 `event_id + document_id` 做 Redis 幂等
7. 如果开启去抖：
   - 写 debounce 快照
   - 投递延迟 flush RQ 任务
8. 如果未开启去抖：
   - 直接投递主 RQ 任务

## RQ 任务

### 主任务

```python
process_document_job(
    document_id: str,
    event_id: str,
    folder_token: str | None = None,
    feishu_ingest_kind: str | None = None,
    feishu_file_type_hint: str | None = None,
)
```

### Flush 任务

```python
flush_debounced_document_job(
    document_id: str,
    version: int,
)
```

## 接入方必须实现

### 1. Feishu 客户端

`webhook_app.create_app(...)` 需要传入一个实现了下面协议的对象：

```python
class FeishuWebhookClient(Protocol):
    def subscribe_drive_file_events(
        self,
        file_token: str,
        *,
        file_type: str = "docx",
    ) -> dict[str, Any]:
        ...

    def subscribe_folder_file_created(self, folder_token: str) -> dict[str, Any]:
        ...
```

### 2. 文档处理 handler

启动时注册：

```python
from feishu_webhook.worker_tasks import configure_document_job_handler


def my_handler(
    document_id: str,
    event_id: str,
    folder_token: str | None,
    feishu_ingest_kind: str | None,
    feishu_file_type_hint: str | None,
) -> None:
    pass


configure_document_job_handler(my_handler)
```

## 启动示例

### Webhook 服务

```python
from feishu_webhook.webhook_app import create_app

app = create_app(feishu_client=my_feishu_client)
```

### Uvicorn

```bash
uvicorn your_entry:app --host 0.0.0.0 --port 18080
```

### Worker

如果用了 debounce，必须确保 RQ worker 开启 scheduler：

```python
worker.work(with_scheduler=True)
```

## 配置建议

```dotenv
REDIS_URL=redis://127.0.0.1:6381/0
VLA_HOST=0.0.0.0
VLA_PORT=18080
VLA_QUEUE_NAME=vla:default
VLA_RQ_JOB_TIMEOUT_SECONDS=3600

FEISHU_API_BASE=https://open.feishu.cn
FEISHU_WEBHOOK_PATH=/webhook/feishu
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_ENCRYPT_KEY=
FEISHU_VERIFICATION_TOKEN=
FEISHU_EVENT_DEDUP_TTL_SECONDS=86400
FEISHU_WEBHOOK_DOC_DEBOUNCE_SECONDS=0
FEISHU_SUBSCRIBE_FOLDER_TOKEN=
FEISHU_AUTO_SUBSCRIBE_DOCX=true
FEISHU_PRESUBSCRIBE_DOCX_TOKENS=
FEISHU_SUBSCRIBE_STATE_TTL_SECONDS=2592000
```

## 迁移注意事项

- 不要把旧 VLA 的 `ServiceBundle` 一起迁过来
- 不要把 OAuth / A2A / LLM / Dify / 审计逻辑一起迁过来
- 幂等键必须保留 `event_id + document_id`
- `extract_feishu_ingest(...)` 必须保留 `cloud_docx / drive_file` 分流语义
- RQ worker 必须启用 scheduler 才能支持 debounce flush

