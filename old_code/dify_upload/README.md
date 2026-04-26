# Dify Upload

最小可复制的 Dify CSV 上传模块。

## 目录

```text
integrations/
  dify_upload/
    __init__.py
    config.py
    http_port.py
    upload.py
```

## 依赖

```bash
pip install httpx
```

## 快速开始

```python
from pathlib import Path

from integrations.dify_upload import (
    DifyUploadConfig,
    SimpleHttpPort,
    upload_csv_document,
)

config = DifyUploadConfig(
    api_base="https://your-dify.example.com",
    api_key="dataset-api-key",
    dataset_id="dataset-uuid",
)

with SimpleHttpPort.from_config(config) as http:
    result = upload_csv_document(
        config,
        Path("qa.csv"),
        http=http,
        upload_filename="qa_upload.csv",
    )

print(result)
```

## 环境变量示例

```env
DIFY_API_BASE=https://your-dify.example.com
DIFY_API_KEY=dataset-api-key
DIFY_DATASET_ID=dataset-uuid
DIFY_HTTP_VERIFY=true
DIFY_TIMEOUT_SECONDS=60
```

## 行为说明

- `api_base` 支持传 `https://host` 或 `https://host/v1`
- 内部会自动补齐 `/v1`
- `dataset_id` / `api_key` 可在调用时覆盖配置值
- `document.id == ""` 会被归一化为 `None`
- HTTP 200 但 `body.code != 0/200` 仍按失败处理

## 不包含

- 路由回退
- 审计
- 重试框架
- 状态机
- 文件清理
