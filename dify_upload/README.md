# dify-upload

最小可用的 Dify CSV 上传模块。

> **`.venv`：** 下述 **`uv venv` / `.\.venv\...` 仅用于维护仓库克隆根**本地调试、单测；**`.cursor/rules/anti-venv.mdc`**。执行工作区 **禁止** 以 `tools/dify_upload/.venv` 作生产工具 **正式** 运行时。

## 边界

- 调用方必须先提供完整 `api_base`、`api_key`、`dataset_id`（`api_key` 在多数部署下为**实例级**；与 `dataset_id` 分工：谁有权访问、写到哪个数据集）
- 本模块不做 `folder_token` 路由
- 本模块不读取运行时上下文
- 本模块只处理 CSV 上传
- 上传参数固定为当前管线已验证合同，不开放额外配置

## 安装（维护仓调试）

```powershell
cd c:\WorkPlace\NewVLA\dify_upload
uv venv --python 3.11 .venv
uv pip install --python .\.venv\Scripts\python.exe -e .[test]
```

## 使用

```python
from pathlib import Path

from dify_upload import DifyTargetConfig, upload_csv_to_dify

target = DifyTargetConfig(
    api_base="https://dify.example.com",
    api_key="your-dify-instance-api-key",
    dataset_id="dataset-123",
    http_verify=True,
    timeout_seconds=60.0,
)

result = upload_csv_to_dify(
    target,
    Path("outputs/qa.csv"),
    upload_filename="qa_upload.csv",
)

print(result.document_id)
print(result.batch)
```

## 成功结果

- 返回 `UploadResult(dataset_id, document_id, batch, response_body)`
- `response_body` 保留原始 JSON，便于上游记录和排障

## 失败语义

- `DifyConfigError`：目标配置不完整或超时非法
- `DifyRequestError`：本地文件问题、网络问题、HTTP 4xx/5xx
- `DifyResponseError`：非 JSON、JSON 结构异常、业务码失败、关键字段缺失

## 测试（维护仓）

```powershell
cd c:\WorkPlace\NewVLA\dify_upload
.\.venv\Scripts\python.exe -m pytest tests -v
```
