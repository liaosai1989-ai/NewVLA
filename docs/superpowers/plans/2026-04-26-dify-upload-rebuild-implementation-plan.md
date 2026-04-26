# Dify Upload Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `c:\WorkPlace\NewVLA\dify_upload` 落地一个只负责 CSV 上传的 Dify 模块，接收已解析完成的目标配置，调用 Dify `create-by-file` 接口，成功时返回结构化结果，失败时稳定区分配置错误、请求错误、响应错误。

**Architecture:** 保持 v1 极简：运行时代码只保留 `config.py`、`upload.py`、`__init__.py` 三个公开模块，不复活旧版 `http_port.py`，也不为未来需求预埋抽象。`config.py` 负责把 `DifyTargetConfig` 收紧成“构造成功就可直接发请求”的目标对象；`upload.py` 负责异常类型、`UploadResult`、本地文件校验、HTTP 请求和响应解析，并内部直接创建短生命周期 `httpx.Client`。

**Tech Stack:** Python 3.11+, `dataclasses`, `pathlib`, `httpx`, `pytest`

---

## Scope Check

只实现 spec 明确要求的 v1 能力：

- 接收完整 `DifyTargetConfig`
- 只支持 `.csv`
- 固定上传参数：
  - `indexing_technique = "high_quality"`
  - `doc_form = "text_model"`
  - `process_rule = {"mode": "automatic"}`
- 直接调用 `{api_base_v1}/datasets/{dataset_id}/document/create-by-file`
- 返回 `UploadResult`
- 抛出 `DifyUploadError` / `DifyConfigError` / `DifyRequestError` / `DifyResponseError`
- 只兼容两条 `document_id` 提取路径：
  - `body["document"]["id"]`
  - `body["data"]["document"]["id"]`
- JSON 解析失败统一按响应错误处理，包括 `json.JSONDecodeError` 和 `ValueError`

明确不做：

- `folder_token` 路由
- 读取 `.env` 或运行时上下文
- 多格式上传
- 可配置 `doc_form` / `process_rule`
- 公共 HTTP 抽象
- 重试框架
- 状态机
- 审计系统

## File Structure

目标目录树：

```text
dify_upload/
├─ pyproject.toml
├─ README.md
├─ src/
│  └─ dify_upload/
│     ├─ __init__.py
│     ├─ config.py
│     └─ upload.py
└─ tests/
   ├─ test_config.py
   └─ test_upload.py
```

设计约束：

- 运行时代码仍然只有 spec 规定的三个模块；`src/` 只是为了让安装和测试边界清楚。
- 不新增 `errors.py`、`http.py`、`client.py`、`models.py` 这类拆分文件。
- `config.py` 负责：
  - `DifyTargetConfig`
  - `api_base_v1` 规范化
  - 构造时校验 `api_base`、`api_key`、`dataset_id`、`timeout_seconds`
- `upload.py` 负责：
  - 四类异常
  - `UploadResult`
  - 本地文件校验
  - HTTP 请求
  - 响应解析
- `__init__.py` 只导出稳定公共接口，不额外承载业务逻辑。
- 测试只覆盖高价值路径，不写只证明“文件还不存在”的噪音步骤。

### Task 1: Bootstrap Environment And The Validated Target Model

**Files:**
- Create: `dify_upload/pyproject.toml`
- Create: `dify_upload/README.md`
- Create: `dify_upload/src/dify_upload/__init__.py`
- Create: `dify_upload/src/dify_upload/config.py`
- Create: `dify_upload/src/dify_upload/upload.py`
- Test: `dify_upload/tests/test_config.py`

- [ ] **Step 1: Bootstrap the local environment**

Run:

```powershell
cd c:\WorkPlace\NewVLA\dify_upload
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install pytest
```

Expected:

- `python --version` shows `Python 3.11` or newer
- `.venv` is created successfully
- `pytest` installs without errors

- [ ] **Step 2: Write the failing test**

`dify_upload/tests/test_config.py`

```python
import pytest

from dify_upload.config import DifyTargetConfig
from dify_upload.upload import DifyConfigError


def test_target_config_normalizes_api_base_and_rejects_invalid_fields():
    plain = DifyTargetConfig(
        api_base="https://dify.example.com",
        api_key="dataset-key",
        dataset_id="dataset-123",
    )
    with_v1 = DifyTargetConfig(
        api_base="https://dify.example.com/v1/",
        api_key="dataset-key",
        dataset_id="dataset-123",
        http_verify=False,
        timeout_seconds=12.5,
    )

    assert plain.api_base_v1 == "https://dify.example.com/v1"
    assert with_v1.api_base_v1 == "https://dify.example.com/v1"
    assert plain.http_verify is True
    assert plain.timeout_seconds == 60.0
    assert with_v1.http_verify is False
    assert with_v1.timeout_seconds == 12.5

    with pytest.raises(DifyConfigError, match="api_base is empty"):
        DifyTargetConfig(
            api_base=" ",
            api_key="dataset-key",
            dataset_id="dataset-123",
        )

    with pytest.raises(DifyConfigError, match="api_key is empty"):
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key=" ",
            dataset_id="dataset-123",
        )

    with pytest.raises(DifyConfigError, match="dataset_id is empty"):
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key="dataset-key",
            dataset_id=" ",
        )

    with pytest.raises(DifyConfigError, match="timeout_seconds must be > 0"):
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key="dataset-key",
            dataset_id="dataset-123",
            timeout_seconds=0,
        )
```

- [ ] **Step 3: Run the test to verify it fails for the right reason**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL because `DifyTargetConfig` validation and `DifyConfigError` do not exist yet

- [ ] **Step 4: Write the minimal implementation**

`dify_upload/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dify-upload"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "httpx>=0.28,<1.0"
]

[project.optional-dependencies]
test = [
  "pytest>=8.3,<9.0"
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`dify_upload/src/dify_upload/upload.py`

```python
from __future__ import annotations


class DifyUploadError(RuntimeError):
    """Base error for dify upload failures."""


class DifyConfigError(DifyUploadError):
    """Raised when the resolved target config is invalid."""


class DifyRequestError(DifyUploadError):
    """Raised when local file checks or the HTTP request fail."""


class DifyResponseError(DifyUploadError):
    """Raised when the Dify response shape or business result is invalid."""
```

`dify_upload/src/dify_upload/config.py`

```python
from __future__ import annotations

from dataclasses import dataclass


def _raise_config_error(message: str) -> None:
    from .upload import DifyConfigError

    raise DifyConfigError(message)


def _require_non_empty(value: str, *, field_name: str, hint: str) -> str:
    text = str(value).strip()
    if not text:
        _raise_config_error(f"dify config error: {field_name} is empty; {hint}")
    return text


@dataclass(frozen=True)
class DifyTargetConfig:
    api_base: str
    api_key: str
    dataset_id: str
    http_verify: bool = True
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        _require_non_empty(
            self.api_base,
            field_name="api_base",
            hint="resolve target config before calling upload",
        )
        _require_non_empty(
            self.api_key,
            field_name="api_key",
            hint="resolve target config before calling upload",
        )
        _require_non_empty(
            self.dataset_id,
            field_name="dataset_id",
            hint="caller must provide dataset_id before upload",
        )
        if self.timeout_seconds <= 0:
            _raise_config_error(
                "dify config error: timeout_seconds must be > 0; caller must provide a positive timeout"
            )

    @property
    def api_base_v1(self) -> str:
        base = self.api_base.strip().rstrip("/")
        if base.endswith("/v1"):
            return base
        return f"{base}/v1"
```

`dify_upload/src/dify_upload/__init__.py`

```python
from .config import DifyTargetConfig

__all__ = ["DifyTargetConfig"]
```

`dify_upload/README.md`

```md
# dify-upload

最小可用的 Dify CSV 上传模块。

边界：

- 调用方必须先提供完整 `api_base`、`api_key`、`dataset_id`
- 本模块不做 `folder_token` 路由
- 本模块不读取运行时上下文
- 本模块只处理 CSV 上传
```

- [ ] **Step 5: Install the package and re-run the test**

Run:

```powershell
cd c:\WorkPlace\NewVLA\dify_upload
.\.venv\Scripts\python.exe -m pip install -e .[test]
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add dify_upload/pyproject.toml dify_upload/README.md dify_upload/src/dify_upload/__init__.py dify_upload/src/dify_upload/config.py dify_upload/src/dify_upload/upload.py dify_upload/tests/test_config.py
git commit -m "feat: bootstrap validated dify target config"
```

### Task 2: Implement The CSV Upload Flow End-To-End

**Files:**
- Modify: `dify_upload/src/dify_upload/upload.py`
- Test: `dify_upload/tests/test_upload.py`

- [ ] **Step 1: Write the failing tests**

`dify_upload/tests/test_upload.py`

```python
import json

import httpx
import pytest

from dify_upload.config import DifyTargetConfig
from dify_upload.upload import (
    DifyRequestError,
    DifyResponseError,
    UploadResult,
    upload_csv_to_dify,
)


class StaticClient:
    response = None
    error = None
    last_init = None
    last_post = None

    def __init__(self, *, verify, timeout, follow_redirects):
        type(self).last_init = {
            "verify": verify,
            "timeout": timeout,
            "follow_redirects": follow_redirects,
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, url, *, headers, files, data):
        type(self).last_post = {
            "url": url,
            "headers": headers,
            "files": files,
            "data": data,
        }
        if type(self).error is not None:
            raise type(self).error
        return type(self).response


def test_upload_posts_fixed_contract_and_returns_structured_result(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_text("question,answer\nq,a\n", encoding="utf-8")

    StaticClient.error = None
    StaticClient.response = type(
        "SuccessResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"document": {"id": "doc_123"}, "batch": "batch_123"},
        },
    )()
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    result = upload_csv_to_dify(
        DifyTargetConfig(
            api_base="https://dify.example.com/",
            api_key="dataset-key",
            dataset_id="dataset-123",
            http_verify=False,
            timeout_seconds=12.5,
        ),
        csv_path,
        upload_filename="upload.csv",
    )

    assert StaticClient.last_init == {
        "verify": False,
        "timeout": 12.5,
        "follow_redirects": False,
    }
    assert StaticClient.last_post["url"] == (
        "https://dify.example.com/v1/datasets/dataset-123/document/create-by-file"
    )
    assert StaticClient.last_post["headers"]["Authorization"] == "Bearer dataset-key"
    assert StaticClient.last_post["files"]["file"] == (
        "upload.csv",
        b"question,answer\nq,a\n",
        "text/csv",
    )
    assert json.loads(StaticClient.last_post["data"]["data"]) == {
        "indexing_technique": "high_quality",
        "doc_form": "text_model",
        "process_rule": {"mode": "automatic"},
    }
    assert result == UploadResult(
        dataset_id="dataset-123",
        document_id="doc_123",
        batch="batch_123",
        response_body={"document": {"id": "doc_123"}, "batch": "batch_123"},
    )


def test_upload_accepts_fallback_document_path(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_text("question,answer\nq,a\n", encoding="utf-8")

    StaticClient.error = None
    StaticClient.response = type(
        "FallbackResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {
                "data": {"document": {"id": "doc_fallback"}},
                "batch": "batch_fallback",
            },
        },
    )()
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    result = upload_csv_to_dify(
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key="dataset-key",
            dataset_id="dataset-123",
        ),
        csv_path,
    )

    assert result.document_id == "doc_fallback"
    assert result.batch == "batch_fallback"


def test_upload_rejects_missing_or_non_csv_file(tmp_path):
    target = DifyTargetConfig(
        api_base="https://dify.example.com",
        api_key="dataset-key",
        dataset_id="dataset-123",
    )

    with pytest.raises(DifyRequestError, match="file does not exist"):
        upload_csv_to_dify(target, tmp_path / "missing.csv")

    txt_path = tmp_path / "qa.txt"
    txt_path.write_text("question,answer\nq,a\n", encoding="utf-8")
    with pytest.raises(DifyRequestError, match="file is not csv"):
        upload_csv_to_dify(target, txt_path)


def test_upload_wraps_request_and_http_failures(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_text("question,answer\nq,a\n", encoding="utf-8")
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    request = httpx.Request("POST", "https://dify.example.com")
    StaticClient.response = None
    StaticClient.error = httpx.ConnectTimeout("boom", request=request)
    with pytest.raises(DifyRequestError, match="upload request failed"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.error = None
    StaticClient.response = type(
        "UnauthorizedResponse",
        (),
        {"status_code": 401, "reason_phrase": "Unauthorized"},
    )()
    with pytest.raises(DifyRequestError, match="status=401 reason=Unauthorized"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )


def test_upload_rejects_invalid_response_shapes_and_business_failures(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_text("question,answer\nq,a\n", encoding="utf-8")
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)
    StaticClient.error = None

    StaticClient.response = type(
        "JsonDecodeResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: (_ for _ in ()).throw(json.JSONDecodeError("bad", "x", 0)),
        },
    )()
    with pytest.raises(DifyResponseError, match="response is not valid JSON"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "ValueErrorResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: (_ for _ in ()).throw(ValueError("bad json")),
        },
    )()
    with pytest.raises(DifyResponseError, match="response is not valid JSON"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "ArrayResponse",
        (),
        {"status_code": 200, "reason_phrase": "OK", "json": lambda self: []},
    )()
    with pytest.raises(DifyResponseError, match="expected JSON object but got list"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "CodeResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"code": 123, "message": "process_rule is required"},
        },
    )()
    with pytest.raises(DifyResponseError, match="api code=123"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "ErrorResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"error": "blocked", "batch": "x", "document": {"id": "y"}},
        },
    )()
    with pytest.raises(DifyResponseError, match="error field is present"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "DocumentMissingResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"batch": "batch_only"},
        },
    )()
    with pytest.raises(DifyResponseError, match="missing document_id"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "BatchMissingResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"document": {"id": "doc_123"}},
        },
    )()
    with pytest.raises(DifyResponseError, match="missing batch"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests/test_upload.py -v`
Expected: FAIL because `upload_csv_to_dify` and `UploadResult` are not implemented yet

- [ ] **Step 3: Implement the full upload flow**

`dify_upload/src/dify_upload/upload.py`

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import DifyTargetConfig


class DifyUploadError(RuntimeError):
    """Base error for dify upload failures."""


class DifyConfigError(DifyUploadError):
    """Raised when the resolved target config is invalid."""


class DifyRequestError(DifyUploadError):
    """Raised when local file checks or the HTTP request fail."""


class DifyResponseError(DifyUploadError):
    """Raised when the Dify response shape or business result is invalid."""


@dataclass(frozen=True)
class UploadResult:
    dataset_id: str
    document_id: str
    batch: str
    response_body: dict[str, Any]


def _read_csv_bytes(csv_path: Path) -> bytes:
    if not csv_path.exists():
        raise DifyRequestError(
            f"dify request error: file does not exist: {csv_path}"
        )
    if csv_path.suffix.lower() != ".csv":
        raise DifyRequestError(
            "dify request error: file is not csv; only .csv is supported in v1"
        )
    try:
        return csv_path.read_bytes()
    except OSError as exc:
        raise DifyRequestError(
            f"dify request error: file is not readable: {csv_path}"
        ) from exc


def _pick_document_id(node: Any) -> str | None:
    if not isinstance(node, dict):
        return None
    raw = node.get("id")
    text = "" if raw is None else str(raw).strip()
    return text or None


def _extract_document_id(body: dict[str, Any]) -> str:
    primary = _pick_document_id(body.get("document"))
    if primary:
        return primary

    data_node = body.get("data")
    if isinstance(data_node, dict):
        fallback = _pick_document_id(data_node.get("document"))
        if fallback:
            return fallback

    raise DifyResponseError("dify response error: missing document_id in response body")


def _parse_json_body(response: Any) -> dict[str, Any]:
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise DifyResponseError(
            "dify response error: response is not valid JSON"
        ) from exc

    if not isinstance(body, dict):
        raise DifyResponseError(
            f"dify response error: expected JSON object but got {type(body).__name__}"
        )
    return body


def _raise_if_business_failed(body: dict[str, Any]) -> None:
    api_code = body.get("code")
    if api_code is not None and api_code not in (0, "0", 200, "200"):
        detail = body.get("message") or body.get("msg") or body
        raise DifyResponseError(
            f"dify response error: api code={api_code} detail={detail}"
        )

    if body.get("error"):
        raise DifyResponseError(
            "dify response error: error field is present in response body"
        )


def upload_csv_to_dify(
    target: DifyTargetConfig,
    csv_path: Path,
    *,
    upload_filename: str | None = None,
) -> UploadResult:
    csv_bytes = _read_csv_bytes(csv_path)
    filename = (upload_filename or "").strip() or csv_path.name
    url = (
        f"{target.api_base_v1}/datasets/"
        f"{target.dataset_id}/document/create-by-file"
    )
    data_payload = json.dumps(
        {
            "indexing_technique": "high_quality",
            "doc_form": "text_model",
            "process_rule": {"mode": "automatic"},
        },
        ensure_ascii=False,
    )

    try:
        with httpx.Client(
            verify=target.http_verify,
            timeout=target.timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {target.api_key}"},
                files={"file": (filename, csv_bytes, "text/csv")},
                data={"data": data_payload},
            )
    except httpx.RequestError as exc:
        raise DifyRequestError(
            f"dify request error: upload request failed: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise DifyRequestError(
            f"dify request error: upload failed with status={response.status_code} reason={response.reason_phrase}; check api_key or api_base"
        )

    body = _parse_json_body(response)
    _raise_if_business_failed(body)

    document_id = _extract_document_id(body)
    batch = str(body.get("batch") or "").strip()
    if not batch:
        raise DifyResponseError("dify response error: missing batch in response body")

    return UploadResult(
        dataset_id=target.dataset_id,
        document_id=document_id,
        batch=batch,
        response_body=body,
    )
```

- [ ] **Step 4: Run the upload tests**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests/test_upload.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dify_upload/src/dify_upload/upload.py dify_upload/tests/test_upload.py
git commit -m "feat: implement dify csv upload flow"
```

### Task 3: Export The Stable API And Finish The README

**Files:**
- Modify: `dify_upload/src/dify_upload/__init__.py`
- Modify: `dify_upload/README.md`
- Modify: `dify_upload/tests/test_config.py`

- [ ] **Step 1: Add the last failing public-API test**

Append to `dify_upload/tests/test_config.py`:

```python
from dify_upload import (
    DifyConfigError,
    DifyRequestError,
    DifyResponseError,
    DifyTargetConfig,
    DifyUploadError,
    UploadResult,
    upload_csv_to_dify,
)


def test_package_root_exports_stable_public_api():
    assert DifyTargetConfig.__name__ == "DifyTargetConfig"
    assert UploadResult.__name__ == "UploadResult"
    assert upload_csv_to_dify.__name__ == "upload_csv_to_dify"
    assert issubclass(DifyConfigError, DifyUploadError)
    assert issubclass(DifyRequestError, DifyUploadError)
    assert issubclass(DifyResponseError, DifyUploadError)
```

- [ ] **Step 2: Run the focused suite to verify it fails**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_upload.py -v`
Expected: FAIL with import error from `dify_upload.__init__`

- [ ] **Step 3: Update exports and README**

`dify_upload/src/dify_upload/__init__.py`

```python
from .config import DifyTargetConfig
from .upload import (
    DifyConfigError,
    DifyRequestError,
    DifyResponseError,
    DifyUploadError,
    UploadResult,
    upload_csv_to_dify,
)

__all__ = [
    "DifyTargetConfig",
    "UploadResult",
    "upload_csv_to_dify",
    "DifyUploadError",
    "DifyConfigError",
    "DifyRequestError",
    "DifyResponseError",
]
```

`dify_upload/README.md`

```md
# dify-upload

最小可用的 Dify CSV 上传模块。

## 边界

- 调用方必须先提供完整 `api_base`、`api_key`、`dataset_id`
- 本模块不做 `folder_token` 路由
- 本模块不读取运行时上下文
- 本模块只处理 CSV 上传
- 上传参数固定为当前管线已验证合同，不开放额外配置

## 安装

```powershell
cd c:\WorkPlace\NewVLA\dify_upload
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[test]
```

## 使用

```python
from pathlib import Path

from dify_upload import DifyTargetConfig, upload_csv_to_dify

target = DifyTargetConfig(
    api_base="https://dify.example.com",
    api_key="dataset-key",
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

## 测试

```powershell
cd c:\WorkPlace\NewVLA\dify_upload
.\.venv\Scripts\python.exe -m pytest tests -v
```
```

- [ ] **Step 4: Run the full suite**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dify_upload/src/dify_upload/__init__.py dify_upload/README.md dify_upload/tests/test_config.py
git commit -m "feat: finalize dify upload public api"
```

## Self-Review

### Spec Coverage

- `DifyTargetConfig` 与 `api_base_v1`：Task 1 覆盖。
- `api_base`、`api_key`、`dataset_id`、`timeout_seconds` 的构造期校验：Task 1 覆盖。
- `UploadResult` 与结构化返回：Task 2 覆盖。
- 固定 URL、固定 multipart 合同、固定上传参数：Task 2 覆盖。
- 禁止公开 HTTP 抽象，内部使用短生命周期 `httpx.Client` 且 `follow_redirects=False`：Task 2 覆盖。
- `document_id` 主路径与 fallback 路径：Task 2 覆盖。
- HTTP/JSON/业务失败/关键字段缺失：Task 2 覆盖。
- 公开导出接口：Task 3 覆盖。
- README 只说明当前合同，不额外扩展：Task 3 覆盖。

### Gaps Check

- 未加入重试、审计、状态机；这是 spec 明确非目标。
- 未新增 `errors.py` / `http_port.py` / `models.py`；这是刻意减法，不是遗漏。
- 未支持非 CSV；这是 spec 明确限制。
- 未单独加“官方 API 预检任务”；这里默认沿用当前已确认的 spec 合同，不再为 v1 额外扩展流程。

### Placeholder Scan

- 计划未使用 `TODO`、`TBD`、`implement later`。
- 每个测试步骤都给了可直接复制的测试代码。
- 每个实现步骤都给了实际文件内容，不依赖“参照前文自行补全”。
- 已去掉单独的“导出面任务”，减少流程膨胀。

Plan complete and saved to `docs/superpowers/plans/2026-04-26-dify-upload-rebuild-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
