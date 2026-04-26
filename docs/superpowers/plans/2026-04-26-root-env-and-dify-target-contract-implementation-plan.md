# Root Env And Dify Target Contract Implementation Plan

## 修订说明（2026-04-27 MarkItDown 固定依赖口径补充）

本文件以下正文保留原文，不直接改写原计划内容。

针对本轮评审已确认“新代码继续使用 `MarkItDown`，但不再暴露 `MARKITDOWN_COMMAND` 配置项”这一口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- `feishu_fetch` 新代码命中需转换格式时，仍固定使用 `MarkItDown`
- 根 `.env`、settings/dataclass、配置加载函数和测试样例中，不再保留 `MARKITDOWN_COMMAND` / `markitdown_command`
- 正文中凡是通过 `MARKITDOWN_COMMAND` 把 `MarkItDown` 暴露为可配置项的代码片段、断言和数据结构，均视为已失效
- 后续落地时，应保留 `MarkItDown` 作为固定实现依赖，而不是把它改造成可切换的配置入口

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `webhook`、`dify_upload`、`feishu_fetch` 同时收口到统一合同：根目录 `.env` 只承载静态基础设施配置，`dify_target_key` 与 `dataset_id` 只承载运行时显式业务目标。

**Architecture:** 保持当前三模块边界，不新增顶层公共 resolver 包。`webhook` 负责把 `folder_token` 显式映射成 `dify_target_key + dataset_id + qa_rule_file` 并写入 `task_context.json`；`dify_upload` 负责从仓库根 `.env` 解析 `DIFY_TARGET_<KEY>_*` 静态配置并完成上传；`feishu_fetch` 负责从仓库根 `.env` 读取自己的静态配置，再继续走现有 `lark-cli` / `MarkItDown` 抓取链路。

**Tech Stack:** Python 3.11+/3.12+/3.13, `pydantic`, `pydantic-settings`, `dataclasses`, `pathlib`, `httpx`, `pytest`, FastAPI

---

## Scope Check

这个 spec 同时碰 `webhook`、`dify_upload`、`feishu_fetch`，但三者不是独立子项目：

- `webhook` 必须先产出新的 `task_context.json` 合同
- `dify_upload` 必须消费新的 `dify_target_key + dataset_id` 运行时合同
- `feishu_fetch` 必须补齐根 `.env` 消费边界，和同一套根配置源对齐

因此这里保留一份联动 plan，不拆成多份 plan，避免把“上游先写入、下游后消费”的接口改动拆散。

明确不做：

- 不新增 `pipeline_config`、`shared_env` 之类公共包
- 不兼容 `old_code/` 下旧 `.env`
- 不给根 `.env` 增加默认 `DIFY_DATASET_ID`
- 不让 LLM 注入 `api_base`、`api_key`、`app_secret`
- 不改 `feishu_fetch` 的正文抓取主路径设计，只补根 `.env` 消费合同

## File Structure

本轮预计触达文件：

```text
webhook/
├─ config/folder_routes.example.json
├─ src/webhook_cursor_executor/
│  ├─ app.py
│  ├─ models.py
│  ├─ scheduler.py
│  ├─ settings.py
│  └─ task_files.py
└─ tests/
   ├─ test_app.py
   ├─ test_scheduler.py
   ├─ test_settings.py
   └─ test_task_files.py

dify_upload/
├─ README.md
├─ src/dify_upload/
│  ├─ __init__.py
│  ├─ config.py
│  └─ upload.py
└─ tests/
   ├─ test_config.py
   └─ test_upload.py

feishu_fetch/
├─ README.md
├─ src/feishu_fetch/
│  ├─ __init__.py
│  ├─ config.py
│  └─ facade.py
└─ tests/
   ├─ test_config.py
   ├─ test_facade.py
   └─ test_models.py
```

设计约束：

- `webhook` 继续使用现有 `settings.py` / `models.py` / `task_files.py` 组合，不引入新路由层。
- `dify_upload` 继续只保留 `config.py` + `upload.py` 两个核心实现文件；新合同仍放在 `config.py` 内部完成。
- `feishu_fetch` 允许新增 `config.py`，因为根 `.env` 读取已经是独立职责；不把配置逻辑塞进 `facade.py` 大文件。
- 所有 `.env` 读取都只认仓库根目录 `.env`，路径统一通过 `Path(__file__).resolve().parents[3] / ".env"` 计算。

### Task 1: Tighten Webhook Folder Route Contract

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/settings.py`
- Modify: `webhook/config/folder_routes.example.json`
- Modify: `webhook/tests/test_settings.py`

- [ ] **Step 1: Install the webhook test environment**

Run:

```powershell
cd c:\WorkPlace\NewVLA\webhook
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e .[test]
```

Expected:

- `.venv` exists
- editable install succeeds
- `pytest` can import `webhook_cursor_executor`

- [ ] **Step 2: Write the failing route-contract tests**

Replace `webhook/tests/test_settings.py` with:

```python
import pytest

from webhook_cursor_executor.settings import ExecutorSettings, load_routing_config


def test_settings_defaults_and_route_loading(tmp_path):
    routes_file = tmp_path / "routes.json"
    routes_file.write_text(
        """
        {
          "pipeline_workspace": {
            "path": "C:\\\\workspaces\\\\pipeline",
            "cursor_timeout_seconds": 7200
          },
          "folder_routes": [
            {
              "folder_token": "fld_team_a",
              "dify_target_key": "team_a",
              "qa_rule_file": "rules/team_a_qa.md",
              "dataset_id": "dataset_team_a"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    settings = ExecutorSettings(folder_routes_file=str(routes_file))
    routing = load_routing_config(settings)

    assert settings.feishu_webhook_path == "/webhook/feishu"
    assert settings.cursor_cli_model == "composer-2-fast"
    assert settings.doc_runlock_ttl_seconds >= settings.cursor_run_timeout_seconds
    assert routing.folder_routes[0].dify_target_key == "team_a"
    assert routing.folder_routes[0].qa_rule_file == "rules/team_a_qa.md"
    assert routing.folder_routes[0].dataset_id == "dataset_team_a"


@pytest.mark.parametrize(
    "qa_rule_file",
    [
        "..\\rules\\team_a_qa.md",
        "rules\\..\\secret.md",
        "C:\\\\temp\\\\team_a_qa.md",
        "/tmp/team_a_qa.md",
        "team_a_qa.md",
    ],
)
def test_route_loading_rejects_unsafe_qa_rule_path(tmp_path, qa_rule_file):
    routes_file = tmp_path / "routes.json"
    routes_file.write_text(
        f"""
        {{
          "pipeline_workspace": {{
            "path": "C:\\\\workspaces\\\\pipeline",
            "cursor_timeout_seconds": 7200
          }},
          "folder_routes": [
            {{
              "folder_token": "fld_team_a",
              "dify_target_key": "team_a",
              "qa_rule_file": "{qa_rule_file}",
              "dataset_id": "dataset_team_a"
            }}
          ]
        }}
        """.strip(),
        encoding="utf-8",
    )

    settings = ExecutorSettings(folder_routes_file=str(routes_file))

    with pytest.raises(ValueError, match="qa_rule_file must stay under rules/"):
        load_routing_config(settings)
```

- [ ] **Step 3: Run the focused route tests to verify they fail**

Run: `cd c:\WorkPlace\NewVLA\webhook; .\.venv\Scripts\python.exe -m pytest tests/test_settings.py -v`

Expected: FAIL because `FolderRoute` does not yet require `dify_target_key` and does not validate `qa_rule_file`

- [ ] **Step 4: Implement the route model and example config changes**

Update `webhook/src/webhook_cursor_executor/settings.py`:

```python
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


def _require_non_empty_text(value: str, *, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _normalize_rule_path(value: str) -> str:
    normalized = str(value).strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized:
        raise ValueError("qa_rule_file must be a non-empty string")
    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "rules":
        raise ValueError("qa_rule_file must stay under rules/")
    return normalized


class PipelineWorkspace(BaseModel):
    path: str
    cursor_timeout_seconds: int = 7200


class FolderRoute(BaseModel):
    folder_token: str
    dify_target_key: str
    qa_rule_file: str
    dataset_id: str

    @field_validator("folder_token", "dify_target_key", "dataset_id", mode="before")
    @classmethod
    def validate_non_empty_text(cls, value: str, info) -> str:
        return _require_non_empty_text(value, field_name=info.field_name)

    @field_validator("qa_rule_file", mode="before")
    @classmethod
    def validate_qa_rule_file(cls, value: str) -> str:
        return _normalize_rule_path(str(value))


class RoutingConfig(BaseModel):
    pipeline_workspace: PipelineWorkspace
    folder_routes: list[FolderRoute]


class ExecutorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    redis_url: str = Field(default="redis://127.0.0.1:6381/0", alias="REDIS_URL")
    vla_queue_name: str = Field(default="vla:default", alias="VLA_QUEUE_NAME")
    feishu_webhook_path: str = Field(default="/webhook/feishu", alias="FEISHU_WEBHOOK_PATH")
    feishu_encrypt_key: str = Field(default="", alias="FEISHU_ENCRYPT_KEY")
    feishu_verification_token: str = Field(default="", alias="FEISHU_VERIFICATION_TOKEN")
    event_seen_ttl_seconds: int = Field(default=86400, alias="EVENT_SEEN_TTL_SECONDS")
    doc_snapshot_ttl_seconds: int = Field(default=86400, alias="DOC_SNAPSHOT_TTL_SECONDS")
    doc_runlock_ttl_seconds: int = Field(default=10800, alias="DOC_RUNLOCK_TTL_SECONDS")
    doc_rerun_ttl_seconds: int = Field(default=86400, alias="DOC_RERUN_TTL_SECONDS")
    run_context_ttl_seconds: int = Field(default=259200, alias="RUN_CONTEXT_TTL_SECONDS")
    run_result_ttl_seconds: int = Field(default=259200, alias="RUN_RESULT_TTL_SECONDS")
    cursor_run_timeout_seconds: int = Field(default=7200, alias="CURSOR_RUN_TIMEOUT_SECONDS")
    folder_routes_file: str = Field(
        default=str(Path(__file__).resolve().parents[2] / "config" / "folder_routes.example.json"),
        alias="FOLDER_ROUTES_FILE",
    )
    cursor_cli_model: str = Field(default="composer-2-fast", alias="CURSOR_CLI_MODEL")
    cursor_cli_command: str = Field(default="cursor", alias="CURSOR_CLI_COMMAND")
    cursor_cli_config_path: str = Field(
        default=str(Path.home() / ".cursor" / "cli-config.json"),
        alias="CURSOR_CLI_CONFIG_PATH",
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> "ExecutorSettings":
        if self.doc_runlock_ttl_seconds < self.cursor_run_timeout_seconds:
            raise ValueError("DOC_RUNLOCK_TTL_SECONDS must be >= CURSOR_RUN_TIMEOUT_SECONDS")
        return self


def load_routing_config(settings: ExecutorSettings) -> RoutingConfig:
    data = json.loads(Path(settings.folder_routes_file).read_text(encoding="utf-8"))
    return RoutingConfig.model_validate(data)


@lru_cache
def get_executor_settings() -> ExecutorSettings:
    return ExecutorSettings()
```

Update `webhook/config/folder_routes.example.json`:

```json
{
  "pipeline_workspace": {
    "path": "C:\\workspaces\\pipeline",
    "cursor_timeout_seconds": 7200
  },
  "folder_routes": [
    {
      "folder_token": "fld_team_a",
      "dify_target_key": "team_a",
      "qa_rule_file": "rules/team_a_qa.md",
      "dataset_id": "dataset_team_a"
    }
  ]
}
```

- [ ] **Step 5: Re-run the route tests**

Run: `cd c:\WorkPlace\NewVLA\webhook; .\.venv\Scripts\python.exe -m pytest tests/test_settings.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add webhook/src/webhook_cursor_executor/settings.py webhook/config/folder_routes.example.json webhook/tests/test_settings.py
git commit -m "feat: tighten webhook folder route contract"
```

### Task 2: Propagate `dify_target_key` Through Webhook Runtime Context

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/app.py`
- Modify: `webhook/src/webhook_cursor_executor/models.py`
- Modify: `webhook/src/webhook_cursor_executor/scheduler.py`
- Modify: `webhook/src/webhook_cursor_executor/task_files.py`
- Modify: `webhook/tests/test_app.py`
- Modify: `webhook/tests/test_scheduler.py`
- Modify: `webhook/tests/test_task_files.py`

- [ ] **Step 1: Write the failing webhook context tests**

Update `webhook/tests/test_task_files.py`:

```python
import json

from webhook_cursor_executor.task_files import write_task_bundle


def test_write_task_bundle_uses_run_dir(tmp_path):
    context = {
        "schema_version": "1",
        "run_id": "run_001",
        "event_id": "evt_1",
        "document_id": "doc_1",
        "folder_token": "fld_team_a",
        "event_type": "drive.file.updated_v1",
        "snapshot_version": 3,
        "dify_target_key": "team_a",
        "qa_rule_file": "rules/team_a_qa.md",
        "dataset_id": "dataset_team_a",
        "workspace_path": str(tmp_path),
        "trigger_source": "feishu_webhook",
        "received_at": "2026-04-26T10:00:00Z",
        "cursor_timeout_seconds": 7200,
    }

    bundle = write_task_bundle(workspace_path=tmp_path, run_id="run_001", context=context)
    saved = json.loads(bundle.context_path.read_text(encoding="utf-8"))
    prompt_text = bundle.prompt_path.read_text(encoding="utf-8")

    assert bundle.outputs_dir.is_dir()
    assert ".cursor_task/run_001" in str(bundle.context_path).replace("\\", "/")
    assert saved["dify_target_key"] == "team_a"
    assert saved["dataset_id"] == "dataset_team_a"
    assert "`dify_target_key` 与 `dataset_id`" in prompt_text
```

Add a reusable route helper near the top of `webhook/tests/test_app.py` and assert the saved snapshot includes `dify_target_key`:

```python
def team_a_route() -> FolderRoute:
    return FolderRoute(
        folder_token="fld_team_a",
        dify_target_key="team_a",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
    )
```

Then use `folder_routes=[team_a_route()]` in every `RoutingConfig(...)` and extend `test_webhook_uses_redis_event_seen_and_enqueues_schedule()` with:

```python
    snapshot = store.load_snapshot("doc_1")
    assert snapshot.dify_target_key == "team_a"
    assert queue.calls[0] == ("schedule_document_job", {"document_id": "doc_1", "version": 1})
```

Add a reusable snapshot helper near the top of `webhook/tests/test_scheduler.py`:

```python
def make_snapshot(*, workspace_path: str, version: int, timeout_seconds: int = 7200) -> DocumentSnapshot:
    return DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_1",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        dify_target_key="team_a",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path=workspace_path,
        cursor_timeout_seconds=timeout_seconds,
        received_at="2026-04-26T10:00:00Z",
        version=version,
    )
```

Use `make_snapshot(...)` in all three scheduler tests and extend `test_launch_uses_workspace_timeout_in_task_context()` with:

```python
    assert saved_context["dify_target_key"] == "team_a"
    assert saved_context["dataset_id"] == "dataset_team_a"
```

- [ ] **Step 2: Run the focused webhook tests to verify they fail**

Run: `cd c:\WorkPlace\NewVLA\webhook; .\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_scheduler.py tests/test_task_files.py -v`

Expected: FAIL because `DocumentSnapshot` and `TaskContext` do not yet carry `dify_target_key`

- [ ] **Step 3: Implement the runtime context propagation**

Update `webhook/src/webhook_cursor_executor/models.py`:

```python
from __future__ import annotations

from pydantic import BaseModel


class DocumentSnapshot(BaseModel):
    event_id: str
    document_id: str
    folder_token: str
    event_type: str
    dify_target_key: str
    qa_rule_file: str
    dataset_id: str
    workspace_path: str
    cursor_timeout_seconds: int
    received_at: str
    version: int


class RerunMarker(BaseModel):
    required: bool = True
    target_version: int
    updated_at: int


class RunContext(BaseModel):
    run_id: str
    document_id: str
    version: int
    event_id: str
    workspace_path: str
    status: str


class RunResult(BaseModel):
    run_id: str
    document_id: str
    version: int
    exit_code: int
    status: str
    summary: str | None = None


class TaskContext(BaseModel):
    schema_version: str
    run_id: str
    event_id: str
    document_id: str
    folder_token: str
    event_type: str
    snapshot_version: int
    dify_target_key: str
    qa_rule_file: str
    dataset_id: str
    workspace_path: str
    trigger_source: str
    received_at: str
    cursor_timeout_seconds: int
```

Update the snapshot construction in `webhook/src/webhook_cursor_executor/app.py`:

```python
        snapshot = DocumentSnapshot(
            event_id=event_id,
            document_id=document_id,
            folder_token=folder_token,
            event_type=event_type,
            dify_target_key=route.dify_target_key,
            qa_rule_file=route.qa_rule_file,
            dataset_id=route.dataset_id,
            workspace_path=routing_config.pipeline_workspace.path,
            cursor_timeout_seconds=routing_config.pipeline_workspace.cursor_timeout_seconds,
            received_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            version=version,
        )
```

Update `webhook/src/webhook_cursor_executor/scheduler.py`:

```python
    task_context = TaskContext(
        schema_version="1",
        run_id=run_id,
        event_id=snapshot.event_id,
        document_id=snapshot.document_id,
        folder_token=snapshot.folder_token,
        event_type=snapshot.event_type,
        snapshot_version=snapshot.version,
        dify_target_key=snapshot.dify_target_key,
        qa_rule_file=snapshot.qa_rule_file,
        dataset_id=snapshot.dataset_id,
        workspace_path=snapshot.workspace_path,
        trigger_source="feishu_webhook",
        received_at=snapshot.received_at,
        cursor_timeout_seconds=snapshot.cursor_timeout_seconds,
    )
```

Update the prompt contract in `webhook/src/webhook_cursor_executor/task_files.py`:

```python
def build_task_prompt(context: dict[str, Any]) -> str:
    run_id = context["run_id"]
    return f"""你正在处理一次由飞书 webhook 自动触发的任务。

任务目标：
- 按当前工作区内的 `AGENTS.md` 与规则文件执行该文档的后续处理流程。
- 本次处理对象为：`document_id={context["document_id"]}`。
- 触发事件类型为：`{context["event_type"]}`。

执行前必须先阅读：
- `AGENTS.md`
- `rules/` 目录
- `.cursor_task/{run_id}/task_context.json`

任务要求：
- 这是一次自动触发任务，不要假设用户会补充额外上下文。
- 你必须先读取 `.cursor_task/{run_id}/task_context.json`，再继续后续任务。
- 你必须再读取 `task_context.json` 中指定的 QA 规则文件。
- 如果规则要求调用工具，按规则执行。
- 不要伪造工具结果。
- 不要从仓库文档或静态规则中推断 Dify 目标。
- 你必须同时使用 `task_context.json` 中显式注入的 `dify_target_key` 与 `dataset_id`。
- 最终结果需要上传到 `dify_target_key` 命中的 Dify 实例下的 `dataset_id`。
"""
```

- [ ] **Step 4: Re-run the focused webhook tests**

Run: `cd c:\WorkPlace\NewVLA\webhook; .\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_scheduler.py tests/test_task_files.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/src/webhook_cursor_executor/app.py webhook/src/webhook_cursor_executor/models.py webhook/src/webhook_cursor_executor/scheduler.py webhook/src/webhook_cursor_executor/task_files.py webhook/tests/test_app.py webhook/tests/test_scheduler.py webhook/tests/test_task_files.py
git commit -m "feat: inject dify target into webhook task context"
```

### Task 3: Resolve Dify Static Targets From Root `.env`

**Files:**
- Modify: `dify_upload/src/dify_upload/config.py`
- Modify: `dify_upload/src/dify_upload/__init__.py`
- Modify: `dify_upload/tests/test_config.py`

- [ ] **Step 1: Install the dify_upload test environment**

Run:

```powershell
cd c:\WorkPlace\NewVLA\dify_upload
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e .[test]
```

Expected:

- `.venv` exists
- editable install succeeds
- `pytest` can import `dify_upload`

- [ ] **Step 2: Write the failing resolver tests**

Replace `dify_upload/tests/test_config.py` with:

```python
from pathlib import Path

import pytest

from dify_upload import (
    DifyConfigError as ExportedDifyConfigError,
    DifyTargetConfig as ExportedDifyTargetConfig,
    DifyUploadError,
    UploadResult,
    upload_csv_to_dify,
)
from dify_upload.config import (
    DifyTargetConfig,
    DifyUploadRequest,
    resolve_dify_target_config,
)
from dify_upload.upload import DifyConfigError


def write_root_env(tmp_path: Path, body: str) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(body.strip() + "\n", encoding="utf-8")
    return env_file


def test_request_and_target_resolution_follow_root_env_contract(tmp_path):
    env_file = write_root_env(
        tmp_path,
        """
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=false
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=12.5
        """,
    )

    resolved = resolve_dify_target_config(
        DifyUploadRequest(dify_target_key=" team_a ", dataset_id=" dataset-123 "),
        env_file=env_file,
    )

    assert resolved.dify_target_key == "team_a"
    assert resolved.dataset_id == "dataset-123"
    assert resolved.api_base_v1 == "https://dify.example.com/v1"
    assert resolved.api_key == "dataset-key"
    assert resolved.http_verify is False
    assert resolved.timeout_seconds == 12.5


def test_request_and_resolver_reject_invalid_runtime_or_env_contract(tmp_path):
    env_file = write_root_env(
        tmp_path,
        """
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60
        """,
    )

    with pytest.raises(DifyConfigError, match="dify_target_key is missing"):
        DifyUploadRequest(dify_target_key=" ", dataset_id="dataset-123")

    with pytest.raises(DifyConfigError, match="dataset_id is missing"):
        DifyUploadRequest(dify_target_key="team_a", dataset_id=" ")

    with pytest.raises(DifyConfigError, match="unknown dify_target_key=team_b"):
        resolve_dify_target_config(
            DifyUploadRequest(dify_target_key="team_b", dataset_id="dataset-123"),
            env_file=env_file,
        )

    forbidden_env = write_root_env(
        tmp_path,
        """
        DIFY_DATASET_ID=legacy-default
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60
        """,
    )
    with pytest.raises(DifyConfigError, match="DIFY_DATASET_ID is not allowed"):
        resolve_dify_target_config(
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            env_file=forbidden_env,
        )


def test_package_root_exports_stable_public_api():
    assert ExportedDifyTargetConfig.__name__ == "DifyTargetConfig"
    assert DifyUploadRequest.__name__ == "DifyUploadRequest"
    assert UploadResult.__name__ == "UploadResult"
    assert upload_csv_to_dify.__name__ == "upload_csv_to_dify"
    assert issubclass(ExportedDifyConfigError, DifyUploadError)
```

- [ ] **Step 3: Run the focused resolver tests to verify they fail**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests/test_config.py -v`

Expected: FAIL because `DifyUploadRequest` and `resolve_dify_target_config()` do not exist yet

- [ ] **Step 4: Implement the root-env resolver**

Replace `dify_upload/src/dify_upload/config.py` with:

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _raise_config_error(message: str) -> None:
    from .upload import DifyConfigError

    raise DifyConfigError(message)


def _root_env_file() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


def _require_non_empty(value: str, *, field_name: str, hint: str) -> str:
    text = str(value).strip()
    if not text:
        _raise_config_error(f"dify config error: {field_name} is missing; {hint}")
    return text


def _parse_bool(raw: str, *, env_name: str) -> bool:
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    _raise_config_error(
        f"dify config error: {env_name} must be a boolean; use true/false in root .env"
    )


def _parse_timeout(raw: str, *, env_name: str) -> float:
    try:
        timeout = float(str(raw).strip())
    except ValueError as exc:
        _raise_config_error(
            f"dify config error: {env_name} must be a number; use a positive timeout in root .env"
        )
        raise AssertionError("unreachable") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        _raise_config_error(
            f"dify config error: {env_name} must be > 0; use a positive timeout in root .env"
        )
    return timeout


def _parse_env_text(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            _raise_config_error(
                f"dify config error: invalid root .env line {line_number}; expected KEY=VALUE"
            )
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            _raise_config_error(
                f"dify config error: invalid root .env line {line_number}; env name is empty"
            )
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        result[key] = value
    return result


def _load_env(env_file: Path | None, environ: Mapping[str, str] | None) -> dict[str, str]:
    path = env_file or _root_env_file()
    values: dict[str, str] = {}
    if path.exists():
        values.update(_parse_env_text(path.read_text(encoding="utf-8")))
    if environ:
        for key, value in environ.items():
            values[str(key)] = str(value)
    return values


def _target_env_key(dify_target_key: str) -> str:
    text = _require_non_empty(
        dify_target_key,
        field_name="dify_target_key",
        hint="runtime must provide the target key explicitly",
    )
    normalized = text.replace("-", "_").replace(" ", "_").upper()
    if not all(char.isalnum() or char == "_" for char in normalized):
        _raise_config_error(
            "dify config error: dify_target_key contains unsupported characters; use letters, numbers, dash or underscore"
        )
    return normalized


@dataclass(frozen=True)
class DifyUploadRequest:
    dify_target_key: str
    dataset_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dify_target_key",
            _require_non_empty(
                self.dify_target_key,
                field_name="dify_target_key",
                hint="runtime must provide the target key explicitly",
            ),
        )
        object.__setattr__(
            self,
            "dataset_id",
            _require_non_empty(
                self.dataset_id,
                field_name="dataset_id",
                hint="runtime must provide dataset_id explicitly",
            ),
        )


@dataclass(frozen=True)
class DifyTargetConfig:
    dify_target_key: str
    dataset_id: str
    api_base: str
    api_key: str
    http_verify: bool
    timeout_seconds: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dify_target_key",
            _require_non_empty(
                self.dify_target_key,
                field_name="dify_target_key",
                hint="runtime must provide the target key explicitly",
            ),
        )
        object.__setattr__(
            self,
            "dataset_id",
            _require_non_empty(
                self.dataset_id,
                field_name="dataset_id",
                hint="runtime must provide dataset_id explicitly",
            ),
        )
        object.__setattr__(
            self,
            "api_base",
            _require_non_empty(
                self.api_base,
                field_name="api_base",
                hint="root .env must define the static Dify API base",
            ),
        )
        object.__setattr__(
            self,
            "api_key",
            _require_non_empty(
                self.api_key,
                field_name="api_key",
                hint="root .env must define the static Dify API key",
            ),
        )
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            _raise_config_error(
                "dify config error: timeout_seconds must be > 0; root .env must define a positive timeout"
            )

    @property
    def api_base_v1(self) -> str:
        base = self.api_base.strip().rstrip("/")
        if base.endswith("/v1"):
            return base
        return f"{base}/v1"


def resolve_dify_target_config(
    request: DifyUploadRequest,
    *,
    env_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> DifyTargetConfig:
    values = _load_env(env_file, environ)
    if str(values.get("DIFY_DATASET_ID", "")).strip():
        _raise_config_error(
            "dify config error: DIFY_DATASET_ID is not allowed in root .env; dataset_id must come from runtime context"
        )

    env_key = _target_env_key(request.dify_target_key)
    prefix = f"DIFY_TARGET_{env_key}_"
    api_base_name = prefix + "API_BASE"
    api_key_name = prefix + "API_KEY"
    verify_name = prefix + "HTTP_VERIFY"
    timeout_name = prefix + "TIMEOUT_SECONDS"

    raw_api_base = str(values.get(api_base_name, ""))
    raw_api_key = str(values.get(api_key_name, ""))
    raw_http_verify = str(values.get(verify_name, ""))
    raw_timeout = str(values.get(timeout_name, ""))

    if not raw_api_base.strip() and not raw_api_key.strip():
        _raise_config_error(
            f"dify config error: unknown dify_target_key={request.dify_target_key}; no matching Dify target config found in root .env"
        )

    return DifyTargetConfig(
        dify_target_key=request.dify_target_key,
        dataset_id=request.dataset_id,
        api_base=_require_non_empty(
            raw_api_base,
            field_name=api_base_name,
            hint="root .env must define the target API base",
        ),
        api_key=_require_non_empty(
            raw_api_key,
            field_name=api_key_name,
            hint="root .env must define the target API key",
        ),
        http_verify=_parse_bool(
            _require_non_empty(
                raw_http_verify,
                field_name=verify_name,
                hint="root .env must define the target HTTP verify flag",
            ),
            env_name=verify_name,
        ),
        timeout_seconds=_parse_timeout(
            _require_non_empty(
                raw_timeout,
                field_name=timeout_name,
                hint="root .env must define the target timeout",
            ),
            env_name=timeout_name,
        ),
    )
```

Update `dify_upload/src/dify_upload/__init__.py`:

```python
from .config import DifyTargetConfig, DifyUploadRequest, resolve_dify_target_config
from .upload import (
    DifyConfigError,
    DifyRequestError,
    DifyResponseError,
    DifyUploadError,
    UploadResult,
    upload_csv_to_dify,
)

__all__ = [
    "DifyUploadRequest",
    "DifyTargetConfig",
    "resolve_dify_target_config",
    "UploadResult",
    "upload_csv_to_dify",
    "DifyUploadError",
    "DifyConfigError",
    "DifyRequestError",
    "DifyResponseError",
]
```

- [ ] **Step 5: Re-run the resolver tests**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests/test_config.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add dify_upload/src/dify_upload/config.py dify_upload/src/dify_upload/__init__.py dify_upload/tests/test_config.py
git commit -m "feat: resolve dify targets from root env"
```

### Task 4: Upload CSV Using Runtime Target Keys Instead Of Full Static Config

**Files:**
- Modify: `dify_upload/src/dify_upload/upload.py`
- Modify: `dify_upload/README.md`
- Modify: `dify_upload/tests/test_upload.py`

- [ ] **Step 1: Rewrite the upload tests around the new runtime contract**

Replace `dify_upload/tests/test_upload.py` with:

```python
import json
from pathlib import Path

import httpx
import pytest

from dify_upload.config import DifyUploadRequest
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


def write_root_env(tmp_path: Path, body: str) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(body.strip() + "\n", encoding="utf-8")
    return env_file


def test_upload_resolves_runtime_target_and_returns_structured_result(tmp_path, monkeypatch):
    env_file = write_root_env(
        tmp_path,
        """
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com/
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=false
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=12.5
        """,
    )
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")

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
        DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
        csv_path,
        upload_filename="upload.csv",
        env_file=env_file,
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
    env_file = write_root_env(
        tmp_path,
        """
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60
        """,
    )
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")

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
        DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
        csv_path,
        env_file=env_file,
    )

    assert result.document_id == "doc_fallback"
    assert result.batch == "batch_fallback"


def test_upload_rejects_missing_or_non_csv_file(tmp_path):
    env_file = write_root_env(
        tmp_path,
        """
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60
        """,
    )

    with pytest.raises(DifyRequestError, match="file does not exist"):
        upload_csv_to_dify(
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            tmp_path / "missing.csv",
            env_file=env_file,
        )

    txt_path = tmp_path / "qa.txt"
    txt_path.write_bytes(b"question,answer\nq,a\n")
    with pytest.raises(DifyRequestError, match="file is not csv"):
        upload_csv_to_dify(
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            txt_path,
            env_file=env_file,
        )


def test_upload_wraps_request_and_http_failures(tmp_path, monkeypatch):
    env_file = write_root_env(
        tmp_path,
        """
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60
        """,
    )
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    request = httpx.Request("POST", "https://dify.example.com")
    StaticClient.response = None
    StaticClient.error = httpx.ConnectTimeout("boom", request=request)
    with pytest.raises(DifyRequestError, match="upload request failed"):
        upload_csv_to_dify(
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            csv_path,
            env_file=env_file,
        )

    StaticClient.error = None
    StaticClient.response = type(
        "UnauthorizedResponse",
        (),
        {"status_code": 401, "reason_phrase": "Unauthorized"},
    )()
    with pytest.raises(DifyRequestError, match="status=401 reason=Unauthorized"):
        upload_csv_to_dify(
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            csv_path,
            env_file=env_file,
        )


def test_upload_rejects_invalid_response_shapes_and_business_failures(tmp_path, monkeypatch):
    env_file = write_root_env(
        tmp_path,
        """
        DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
        DIFY_TARGET_TEAM_A_API_KEY=dataset-key
        DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
        DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60
        """,
    )
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")
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
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            csv_path,
            env_file=env_file,
        )

    StaticClient.response = type(
        "ArrayResponse",
        (),
        {"status_code": 200, "reason_phrase": "OK", "json": lambda self: []},
    )()
    with pytest.raises(DifyResponseError, match="expected JSON object but got list"):
        upload_csv_to_dify(
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            csv_path,
            env_file=env_file,
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
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            csv_path,
            env_file=env_file,
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
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            csv_path,
            env_file=env_file,
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
            DifyUploadRequest(dify_target_key="team_a", dataset_id="dataset-123"),
            csv_path,
            env_file=env_file,
        )
```

- [ ] **Step 2: Run the upload tests to verify they fail**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests/test_upload.py -v`

Expected: FAIL because `upload_csv_to_dify()` still expects a pre-resolved `DifyTargetConfig`

- [ ] **Step 3: Switch the uploader to resolve its own target and update the README**

Update `dify_upload/src/dify_upload/upload.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import httpx

from .config import DifyTargetConfig, DifyUploadRequest, resolve_dify_target_config


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
        raise DifyRequestError(f"dify request error: file does not exist: {csv_path}")
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
    request: DifyUploadRequest,
    csv_path: Path,
    *,
    upload_filename: str | None = None,
    env_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> UploadResult:
    target: DifyTargetConfig = resolve_dify_target_config(
        request,
        env_file=env_file,
        environ=environ,
    )
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
    raw_batch = body.get("batch")
    batch = "" if raw_batch is None else str(raw_batch).strip()
    if not batch:
        raise DifyResponseError("dify response error: missing batch in response body")

    return UploadResult(
        dataset_id=target.dataset_id,
        document_id=document_id,
        batch=batch,
        response_body=body,
    )
```

Update `dify_upload/README.md`:

````md
# dify-upload

最小可用的 Dify CSV 上传模块。

## 边界

- 调用方必须显式提供 `dify_target_key` 与 `dataset_id`
- 根目录 `.env` 只提供 `DIFY_TARGET_<KEY>_API_BASE`、`API_KEY`、`HTTP_VERIFY`、`TIMEOUT_SECONDS`
- 根目录 `.env` 禁止提供默认 `DIFY_DATASET_ID`
- 本模块不做 `folder_token` 路由
- 本模块只处理 CSV 上传

## 使用

```python
from pathlib import Path

from dify_upload import DifyUploadRequest, upload_csv_to_dify

result = upload_csv_to_dify(
    DifyUploadRequest(
        dify_target_key="team_a",
        dataset_id="dataset-123",
    ),
    Path(".cursor_task/run_001/outputs/qa.csv"),
)

print(result.document_id)
print(result.batch)
```

## 根 `.env` 示例

```dotenv
DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com
DIFY_TARGET_TEAM_A_API_KEY=dataset-key
DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60
```
````

- [ ] **Step 4: Run the full dify_upload suite**

Run: `cd c:\WorkPlace\NewVLA\dify_upload; .\.venv\Scripts\python.exe -m pytest tests -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dify_upload/src/dify_upload/upload.py dify_upload/README.md dify_upload/tests/test_upload.py
git commit -m "feat: upload csv with runtime dify target"
```

### Task 5: Read Feishu Static Config From Root `.env`

**Files:**
- Create: `feishu_fetch/src/feishu_fetch/config.py`
- Modify: `feishu_fetch/src/feishu_fetch/__init__.py`
- Modify: `feishu_fetch/src/feishu_fetch/facade.py`
- Modify: `feishu_fetch/README.md`
- Create: `feishu_fetch/tests/test_config.py`
- Modify: `feishu_fetch/tests/test_facade.py`
- Modify: `feishu_fetch/tests/test_models.py`

- [ ] **Step 1: Install the feishu_fetch test environment**

Run:

```powershell
cd c:\WorkPlace\NewVLA\feishu_fetch
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e .[test]
```

Expected:

- `.venv` exists
- editable install succeeds
- `pytest` can import `feishu_fetch`

- [ ] **Step 2: Add failing config and facade tests**

Create `feishu_fetch/tests/test_config.py`:

```python
from pathlib import Path

import pytest

from feishu_fetch import FeishuFetchError
from feishu_fetch.config import load_feishu_fetch_settings


def write_root_env(tmp_path: Path, body: str) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(body.strip() + "\n", encoding="utf-8")
    return env_file


def test_load_settings_reads_root_env(tmp_path):
    env_file = write_root_env(
        tmp_path,
        """
        FEISHU_APP_ID=app_123
        FEISHU_APP_SECRET=secret_123
        FEISHU_REQUEST_TIMEOUT_SECONDS=45
        LARK_CLI_COMMAND=custom-lark
        MARKITDOWN_COMMAND=markitdown
        """,
    )

    settings = load_feishu_fetch_settings(env_file=env_file)

    assert settings.feishu_app_id == "app_123"
    assert settings.feishu_app_secret == "secret_123"
    assert settings.request_timeout_seconds == 45.0
    assert settings.lark_cli_command == "custom-lark"
    assert settings.markitdown_command == "markitdown"


def test_load_settings_rejects_missing_required_values(tmp_path):
    env_file = write_root_env(
        tmp_path,
        """
        FEISHU_APP_SECRET=secret_123
        """,
    )

    with pytest.raises(FeishuFetchError) as exc:
        load_feishu_fetch_settings(env_file=env_file)

    assert exc.value.code == "config_error"
    assert "FEISHU_APP_ID" in str(exc.value)
```

Append to `feishu_fetch/tests/test_facade.py`:

```python
def test_cloud_docx_uses_root_env_lark_command(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "FEISHU_APP_ID=app_123",
                "FEISHU_APP_SECRET=secret_123",
                "LARK_CLI_COMMAND=custom-lark",
                "FEISHU_REQUEST_TIMEOUT_SECONDS=30",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args == ["custom-lark", "--help"]:
            return FakeCompletedProcess(stdout="usage")
        if args[:3] == ["custom-lark", "docs", "+fetch"]:
            payload = {
                "data": {
                    "document": {
                        "title": "Weekly Sync",
                        "content": "<doc><p>Hello</p></doc>",
                    }
                }
            }
            return FakeCompletedProcess(stdout=json.dumps(payload, ensure_ascii=False))
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "custom-lark" else None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            document_id="doccnxxxx",
            output_dir=tmp_path / "outputs",
        ),
        env_file=env_file,
    )

    assert Path(result.artifact_path).exists()
    assert calls[0] == ["custom-lark", "--help"]
    assert calls[1][:3] == ["custom-lark", "docs", "+fetch"]
```

Append to `feishu_fetch/tests/test_models.py`:

```python
from feishu_fetch.config import FeishuFetchSettings


def test_settings_dataclass_shape_is_stable():
    settings = FeishuFetchSettings(
        feishu_app_id="app_123",
        feishu_app_secret="secret_123",
        request_timeout_seconds=60.0,
        lark_cli_command="lark-cli",
        markitdown_command="markitdown",
    )

    assert settings.lark_cli_command == "lark-cli"
    assert settings.markitdown_command == "markitdown"
```

- [ ] **Step 3: Run the focused feishu_fetch tests to verify they fail**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_models.py tests/test_facade.py -v`

Expected: FAIL because `load_feishu_fetch_settings()` and `fetch_feishu_content(..., env_file=...)` do not exist yet

- [ ] **Step 4: Implement the root-env settings loader and wire it into the facade**

Create `feishu_fetch/src/feishu_fetch/config.py`:

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .errors import build_error


def _root_env_file() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


def _parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _load_env(env_file: Path | None, environ: Mapping[str, str] | None) -> dict[str, str]:
    path = env_file or _root_env_file()
    values: dict[str, str] = {}
    if path.exists():
        values.update(_parse_env_text(path.read_text(encoding="utf-8")))
    if environ:
        for key, value in environ.items():
            values[str(key)] = str(value)
    return values


def _require_non_empty(values: Mapping[str, str], env_name: str) -> str:
    text = str(values.get(env_name, "")).strip()
    if not text:
        raise build_error(
            code="config_error",
            reason=f"根 .env 缺少 {env_name}",
            advice=f"把 {env_name} 写入仓库根目录 .env 后重试",
            detail={"env_name": env_name},
        )
    return text


@dataclass(frozen=True)
class FeishuFetchSettings:
    feishu_app_id: str
    feishu_app_secret: str
    request_timeout_seconds: float = 60.0
    lark_cli_command: str = "lark-cli"
    markitdown_command: str = "markitdown"

    def __post_init__(self) -> None:
        if not math.isfinite(self.request_timeout_seconds) or self.request_timeout_seconds <= 0:
            raise build_error(
                code="config_error",
                reason="FEISHU_REQUEST_TIMEOUT_SECONDS 必须是大于 0 的有限数字",
                advice="把 FEISHU_REQUEST_TIMEOUT_SECONDS 改为正数后重试",
                detail={"request_timeout_seconds": self.request_timeout_seconds},
            )


def load_feishu_fetch_settings(
    *,
    env_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> FeishuFetchSettings:
    values = _load_env(env_file, environ)
    raw_timeout = str(values.get("FEISHU_REQUEST_TIMEOUT_SECONDS", "60")).strip() or "60"
    try:
        request_timeout_seconds = float(raw_timeout)
    except ValueError as exc:
        raise build_error(
            code="config_error",
            reason="FEISHU_REQUEST_TIMEOUT_SECONDS 不是合法数字",
            advice="把 FEISHU_REQUEST_TIMEOUT_SECONDS 改为正数后重试",
            detail={"FEISHU_REQUEST_TIMEOUT_SECONDS": raw_timeout},
        ) from exc
    lark_cli_command = str(values.get("LARK_CLI_COMMAND", "lark-cli")).strip() or "lark-cli"
    markitdown_command = str(values.get("MARKITDOWN_COMMAND", "markitdown")).strip() or "markitdown"
    return FeishuFetchSettings(
        feishu_app_id=_require_non_empty(values, "FEISHU_APP_ID"),
        feishu_app_secret=_require_non_empty(values, "FEISHU_APP_SECRET"),
        request_timeout_seconds=request_timeout_seconds,
        lark_cli_command=lark_cli_command,
        markitdown_command=markitdown_command,
    )
```

Update `feishu_fetch/src/feishu_fetch/facade.py` with these targeted changes:

```python
from .config import FeishuFetchSettings, load_feishu_fetch_settings
from .errors import FeishuFetchError, build_error
from .models import FeishuFetchRequest, FeishuFetchResult


def _timeout_for(request: FeishuFetchRequest, settings: FeishuFetchSettings) -> float:
    return float(request.timeout_seconds or settings.request_timeout_seconds)


def _ensure_lark_cli_available(*, command: str, timeout_seconds: float) -> None:
    completed = _run_command([command, "--help"], timeout_seconds=timeout_seconds)
    if completed.returncode != 0:
        raise build_error(
            code="dependency_error",
            reason="lark-cli 无法正常启动",
            advice="先在终端手动执行配置中的 LARK_CLI_COMMAND --help，确认安装与 PATH 正常",
            detail={
                "command": [command, "--help"],
                "exit_code": completed.returncode,
                "stderr_tail": completed.stderr[-500:],
            },
        )
```

Update all literal `lark-cli` arguments in `feishu_fetch/src/feishu_fetch/facade.py`:

```python
def _fetch_cloud_docx(request: FeishuFetchRequest, settings: FeishuFetchSettings) -> FeishuFetchResult:
    output_dir = _ensure_output_dir(request.output_dir)
    args = [
        settings.lark_cli_command,
        "docs",
        "+fetch",
        "--api-version",
        "v2",
        "--format",
        "json",
        "--doc-format",
        "xml",
        "--detail",
        "simple",
        "--scope",
        "docx",
        "--document-id",
        request.document_id or "",
    ]
    completed = _run_command(args, timeout_seconds=_timeout_for(request, settings))
    stdout = _require_success(
        completed,
        args=args,
        ingest_kind="cloud_docx",
        doc_type=None,
    )
    payload = _parse_json(
        stdout,
        args=args,
        ingest_kind="cloud_docx",
        doc_type=None,
    )
    document = (((payload.get("data") or {}).get("document")) or {})
    content = str(document.get("content") or "")
    if not content.strip():
        raise build_error(
            code="empty_content",
            reason="抓取成功但正文为空",
            advice="确认目标文档是否有正文内容，或改用人工核查该文档",
            detail={"command": args, "ingest_kind": "cloud_docx"},
        )
    title = _title_for(request, str(document.get("title") or "").strip())
    artifact = _write_text_artifact(
        output_dir,
        base_name=_slugify(title, fallback="cloud-docx"),
        suffix=".xml",
        content=content,
    )
    return FeishuFetchResult(
        artifact_path=str(artifact.resolve()),
        ingest_kind="cloud_docx",
        title=title,
    )
```

```python
def _download_drive_file(
    request: FeishuFetchRequest,
    *,
    output_dir: Path,
    settings: FeishuFetchSettings,
) -> Path:
    download_dir = output_dir / "_raw_download"
    download_dir.mkdir(parents=True, exist_ok=True)
    existing_files = {
        item.resolve() for item in _list_candidate_files(download_dir)
    }
    args = [
        settings.lark_cli_command,
        "drive",
        "+download",
        "--file-token",
        request.file_token or "",
        "--output-dir",
        str(download_dir),
    ]
    completed = _run_command(args, timeout_seconds=_timeout_for(request, settings))
    _require_success(
        completed,
        args=args,
        ingest_kind="drive_file",
        doc_type=request.doc_type,
    )
    return _pick_new_file(download_dir, existing_files=existing_files)
```

```python
def _export_drive_file(
    request: FeishuFetchRequest,
    *,
    output_dir: Path,
    settings: FeishuFetchSettings,
) -> Path:
    export_format = EXPORT_FORMATS[request.doc_type or ""]
    deadline = time.monotonic() + _timeout_for(request, settings)
    args = [
        settings.lark_cli_command,
        "drive",
        "+export",
        "--file-token",
        request.file_token or "",
        "--export-format",
        export_format,
    ]
    completed = _run_command(args, timeout_seconds=_timeout_for(request, settings))
    stdout = _require_success(
        completed,
        args=args,
        ingest_kind="drive_file",
        doc_type=request.doc_type,
    )
    payload = _parse_json(
        stdout,
        args=args,
        ingest_kind="drive_file",
        doc_type=request.doc_type,
    )
    export_file_token = _extract_export_file_token(payload)
    if not export_file_token:
        task_id = _extract_task_id(payload)
        if not task_id:
            raise build_error(
                code="runtime_error",
                reason="导出命令返回结果异常，既没有 file_token 也没有 task_id",
                advice="确认当前 lark-cli 版本和导出命令返回结构是否符合预期",
                detail={
                    "ingest_kind": "drive_file",
                    "doc_type": request.doc_type,
                    "command": args,
                },
            )
        export_file_token = _poll_export_file_token(
            task_id=task_id,
            request=request,
            deadline=deadline,
        )
    download_dir = output_dir / "_raw_export"
    download_dir.mkdir(parents=True, exist_ok=True)
    existing_files = {
        item.resolve()
        for item in _list_candidate_files(
            download_dir,
            allowed_suffixes={f".{export_format}"},
        )
    }
    download_args = [
        settings.lark_cli_command,
        "drive",
        "+export-download",
        "--file-token",
        export_file_token,
        "--output-dir",
        str(download_dir),
    ]
    completed = _run_command(
        download_args,
        timeout_seconds=max(1.0, deadline - time.monotonic()),
    )
    _require_success(
        completed,
        args=download_args,
        ingest_kind="drive_file",
        doc_type=request.doc_type,
    )
    return _pick_new_file(
        download_dir,
        existing_files=existing_files,
        allowed_suffixes={f".{export_format}"},
    )
```

```python
def _fetch_drive_file(
    request: FeishuFetchRequest,
    settings: FeishuFetchSettings,
) -> FeishuFetchResult:
    output_dir = _ensure_output_dir(request.output_dir)
    if request.doc_type == "file":
        source_path = _download_drive_file(
            request,
            output_dir=output_dir,
            settings=settings,
        )
    else:
        source_path = _export_drive_file(
            request,
            output_dir=output_dir,
            settings=settings,
        )
    return _finalize_drive_artifact(
        request,
        source_path=source_path,
        output_dir=output_dir,
    )
```

Update the public entrypoint at the end of `feishu_fetch/src/feishu_fetch/facade.py`:

```python
def fetch_feishu_content(
    request: FeishuFetchRequest,
    *,
    env_file: Path | None = None,
    environ: dict[str, str] | None = None,
) -> FeishuFetchResult:
    settings = load_feishu_fetch_settings(env_file=env_file, environ=environ)
    timeout_seconds = _timeout_for(request, settings)
    _ensure_lark_cli_available(
        command=settings.lark_cli_command,
        timeout_seconds=timeout_seconds,
    )

    if request.ingest_kind == "cloud_docx":
        return _fetch_cloud_docx(request, settings)
    if request.ingest_kind == "drive_file":
        return _fetch_drive_file(request, settings)

    raise FeishuFetchError(
        code="runtime_error",
        llm_message="飞书正文抓取失败：ingest_kind 未命中已知路径。\n处理建议：检查请求中的 ingest_kind 是否正确。",
        detail={"ingest_kind": request.ingest_kind},
    )
```

Update `feishu_fetch/src/feishu_fetch/__init__.py`:

```python
from .config import FeishuFetchSettings, load_feishu_fetch_settings
from .errors import FeishuFetchError
from .facade import fetch_feishu_content
from .models import FeishuFetchRequest, FeishuFetchResult

__all__ = [
    "FeishuFetchError",
    "FeishuFetchSettings",
    "load_feishu_fetch_settings",
    "FeishuFetchRequest",
    "FeishuFetchResult",
    "fetch_feishu_content",
]
```

Update `feishu_fetch/README.md`:

````md
# feishu-fetch

最小可用的飞书正文抓取模块。

## 根 `.env` 合同

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_REQUEST_TIMEOUT_SECONDS`
- `LARK_CLI_COMMAND`
- `MARKITDOWN_COMMAND`

所有静态配置都从仓库根目录 `.env` 读取；运行时请求只提供 `document_id`、`file_token`、`doc_type`、`output_dir` 这类业务参数。

## 使用方式

```python
from pathlib import Path

from feishu_fetch import FeishuFetchRequest, fetch_feishu_content

result = fetch_feishu_content(
    FeishuFetchRequest(
        ingest_kind="cloud_docx",
        document_id="doccnxxxx",
        output_dir=Path(".cursor_task/run_001/outputs/feishu_fetch"),
    )
)
```
````

- [ ] **Step 5: Run the full feishu_fetch suite**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_models.py tests/test_facade.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add feishu_fetch/src/feishu_fetch/config.py feishu_fetch/src/feishu_fetch/__init__.py feishu_fetch/src/feishu_fetch/facade.py feishu_fetch/README.md feishu_fetch/tests/test_config.py feishu_fetch/tests/test_facade.py feishu_fetch/tests/test_models.py
git commit -m "feat: load feishu static config from root env"
```

## Self-Review

### Spec Coverage

- 根 `.env` 是统一静态配置源：Task 1、Task 3、Task 5 覆盖。
- `webhook` 必须写入 `dify_target_key + dataset_id + qa_rule_file`：Task 1、Task 2 覆盖。
- `qa_rule_file` 必须位于 `rules/` 且禁止绝对路径、`..`：Task 1 覆盖。
- `dify_upload` 必须只接收运行时 `dify_target_key + dataset_id`，静态配置自行从根 `.env` 读取：Task 3、Task 4 覆盖。
- 根 `.env` 禁止非空 `DIFY_DATASET_ID`：Task 3 覆盖。
- `unknown dify_target_key`、缺失运行时字段、空字符串都要 fail fast：Task 3 覆盖。
- `feishu_fetch` 直接读取根 `.env` 的静态配置，运行时仍只收业务参数：Task 5 覆盖。
- `old_code/` 下旧 `.env` 不再进入主链路：Task 3 和 Task 5 都通过固定 `parents[3] / ".env"` 覆盖。

### Gaps Check

- 没有新增顶层公共配置包；这是 spec 明确非目标。
- 没有把 `folder_token -> dataset_id` 映射塞回根 `.env`；仍保留在 `webhook/config/folder_routes.example.json`。
- 没有让 `webhook` 直接注入 `api_base`、`api_key`；仍由 `dify_upload` 自己读取。
- 没有改动 `feishu_fetch` 的正文抓取矩阵；只补静态配置读取，不扩展抓取能力。

### Placeholder Scan

- 计划未使用 `TBD`、`TODO`、`implement later`。
- 每个代码步骤都给了实际代码，不依赖“参考前文自行补齐”。
- 每个测试步骤都给了可执行命令与明确失败原因。
- 每个任务都以可单独提交的最小闭环收束。

Plan complete and saved to `docs/superpowers/plans/2026-04-26-root-env-and-dify-target-contract-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
