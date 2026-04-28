# Webhook Cursor Executor Implementation Plan

> **落地状态：已落地**（2026-04-28；实现见 `webhook/src/webhook_cursor_executor/`；运维与升级口径见 `webhook/操作手册.md`；文首修订说明与 `BugList.md` BUG-001 为差异真源。）

## 修订说明（2026-04-28 `ingest_kind` 与 task-context 合同）

- **合同真源**：凡 **字段表、`dify_target_key`、`ingest_kind`、folder 路由（`.env` 优先 / JSON 回退）、Redis 旧快照、单次交付边界** 与本文旧表述冲突时，以 [2026-04-28-task-context-bootstrap-sample-agent-contract-design.md](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) **全文**为准；文首 **「单次交付，禁止拆分」** 覆盖任何「可拆 PR」「紧邻 PR」类旧措辞。
- **`ingest_kind` 写入 `DocumentSnapshot` / `TaskContext` / 落盘 `task_context.json`** 属该 spec 文首交付范围（§7.2–§7.6）；与 [2026-04-28-production-bootstrap-deployment-implementation-plan.md](2026-04-28-production-bootstrap-deployment-implementation-plan.md) 文首「task-context / feishu_fetch 合同同期交付」**同验收窗口**。**本 plan 正文**若仍描述旧字段表，以 **task-context-bootstrap spec §3** 为字段真源。
- 本条 **不撤回** 本 plan 已落地的 Cursor PATH、验签等结论；仅追加 **合同字段与批次** 索引。

## 修订说明（2026-04-27 `cursor` 仅 PATH、正文代码片段中 `CURSOR_CLI_COMMAND` 已过时）

本 plan 以下正文**保留原文**，不整段替换。正文中若出现 `cursor_cli_command` / `CURSOR_CLI_COMMAND`、或 `launch_cursor_agent(..., command=settings.cursor_cli_command)` 等，均视为**历史草稿**，与**当前仓库实现**不一致。

**当前实现要点（以源码为准）**：

- `webhook/src/webhook_cursor_executor/cursor_cli.py`：固定 `cursor`，`shutil.which` 后执行；`launch_cursor_agent` **无** `command` 参数。
- `webhook/src/webhook_cursor_executor/settings.py`：**无** `cursor_cli_command` 字段；根 `.env` 或环境变量出现 `CURSOR_CLI_COMMAND` → 构造 `ExecutorSettings` 即失败（阻断启动，避免静默旁路）。
- `webhook/src/webhook_cursor_executor/scheduler.py`：PATH 未找到可执行文件时 `finalize` 为失败，summary 含 `cursor_not_in_path:`。

升级与运维说明见 `webhook/操作手册.md`、本仓 `ENV-OLD-TO-NEW.md`。

---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `c:\WorkPlace\NewVLA\webhook` 内落地一个可运行的 webhook 调度模块，严格按 spec 实现飞书协议层幂等、`document_id` 调度合并、`folder_token` 路由、`.cursor_task/{run_id}/` 注入目录、Max Mode 同步后启动 Cursor CLI。

**Architecture:** 采用“少文件、强闭环”的 v1 方案。HTTP 入口、Redis 状态机、Cursor 启动器、RQ 入口各占一层，但不额外引入 `queue.py` / `jobs.py` 空壳。所有核心状态统一走 Redis；路由只在 webhook 入口解析一次并固化进 snapshot；`launch` 直接消费 snapshot，避免双真源。

**Tech Stack:** Python 3.13, FastAPI, Redis, RQ, Pydantic v2, Pytest, Fakeredis, HTTPX, PyCryptodome

---

## Scope Check

实现只覆盖 v1 必需项：

- 飞书 webhook challenge / 验签 / 解密 / 事件解析
- `event_id` 协议层幂等，必须用 Redis `SET NX EX`
- `document_id` 级 snapshot / version / runlock / rerun
- 单 workspace + `folder_token` 路由
- `.cursor_task/{run_id}/task_prompt.md` 与 `task_context.json`
- spawn 前同步 Cursor CLI `maxMode`
- `schedule / launch / finalize` 三段式 RQ 任务
- `finalize` 落盘 run result
- 提供真实可运行的 app / worker 装配入口

明确不做：

- runlock 心跳/续租
- 多 workspace 路由
- 复杂优先级调度
- 长期数据库审计
- 低价值“纯转调”测试

## File Structure

减法后的目标文件树：

```text
webhook/
├─ pyproject.toml
├─ README.md
├─ config/
│  └─ folder_routes.example.json
├─ src/
│  └─ webhook_cursor_executor/
│     ├─ __init__.py
│     ├─ settings.py     # env 与 routes 文件加载
│     ├─ models.py       # snapshot/rerun/run-context/run-result/task-context
│     ├─ state_store.py  # event_seen/version/snapshot/runlock/rerun/run-result
│     ├─ task_files.py   # .cursor_task/{run_id}/ 注入目录与 prompt/context 文件
│     ├─ cursor_cli.py   # Max Mode 同步与 Cursor agent 启动
│     ├─ scheduler.py    # schedule/launch/finalize
│     ├─ app.py          # FastAPI app + webhook ingress + build_app()
│     └─ worker.py       # RQ queue/build_worker_runtime/任务入口
└─ tests/
   ├─ conftest.py
   ├─ test_settings.py
   ├─ test_state_store.py
   ├─ test_task_files.py
   ├─ test_cursor_cli.py
   ├─ test_app.py
   └─ test_scheduler.py
```

设计约束：

- `state_store.py` 内聚 Redis keys 与 TTL 语义，不再拆 `redis_keys.py`。
- `app.py` 负责 challenge、验签、解密、事件解析、event_seen、snapshot 更新、schedule 入队。
- `worker.py` 负责真实 RQ 入口与 runtime 装配，不再拆 `queue.py` / `jobs.py`。
- 路由命中结果在 webhook 入口写入 snapshot；`launch` 不再重新查 route。
- `finalize` 必须先写 run result，再清 context、释放 runlock、处理 rerun。

### Task 1: Bootstrap Package, Settings, And Route Loading

**Files:**
- Create: `webhook/pyproject.toml`
- Create: `webhook/README.md`
- Create: `webhook/config/folder_routes.example.json`
- Create: `webhook/src/webhook_cursor_executor/__init__.py`
- Create: `webhook/src/webhook_cursor_executor/settings.py`
- Test: `webhook/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
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
    assert routing.folder_routes[0].dataset_id == "dataset_team_a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webhook_cursor_executor'`

- [ ] **Step 3: Write minimal implementation**

`webhook/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "webhook-cursor-executor"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "fastapi>=0.115,<1.0",
  "redis>=6.0,<7.0",
  "rq>=2.2,<3.0",
  "pydantic>=2.11,<3.0",
  "pydantic-settings>=2.9,<3.0",
  "pycryptodome>=3.21,<4.0"
]

[project.optional-dependencies]
test = [
  "pytest>=8.3,<9.0",
  "fakeredis>=2.29,<3.0",
  "httpx>=0.28,<1.0"
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`webhook/src/webhook_cursor_executor/__init__.py`

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

`webhook/config/folder_routes.example.json`

```json
{
  "pipeline_workspace": {
    "path": "C:\\workspaces\\pipeline",
    "cursor_timeout_seconds": 7200
  },
  "folder_routes": [
    {
      "folder_token": "fld_team_a",
      "qa_rule_file": "rules/team_a_qa.md",
      "dataset_id": "dataset_team_a"
    }
  ]
}
```

`webhook/src/webhook_cursor_executor/settings.py`

```python
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


class PipelineWorkspace(BaseModel):
    path: str
    cursor_timeout_seconds: int = 7200


class FolderRoute(BaseModel):
    folder_token: str
    qa_rule_file: str
    dataset_id: str


class RoutingConfig(BaseModel):
    pipeline_workspace: PipelineWorkspace
    folder_routes: list[FolderRoute]


class ExecutorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
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

`webhook/README.md`

```md
# webhook-cursor-executor

飞书 webhook -> Redis -> RQ -> Cursor CLI 执行器。

v1 范围：

- 飞书 challenge / 验签 / 解密
- Redis `event_seen` 幂等
- `document_id` 级 schedule / launch / finalize
- `.cursor_task/{run_id}` 注入目录
- spawn 前同步 Cursor CLI `maxMode`
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/pyproject.toml webhook/README.md webhook/config/folder_routes.example.json webhook/src/webhook_cursor_executor/__init__.py webhook/src/webhook_cursor_executor/settings.py webhook/tests/test_settings.py
git commit -m "feat: bootstrap webhook executor settings"
```

### Task 2: Add Redis State Store With Event Seen And Run Result

**Files:**
- Create: `webhook/src/webhook_cursor_executor/models.py`
- Create: `webhook/src/webhook_cursor_executor/state_store.py`
- Test: `webhook/tests/test_state_store.py`

- [ ] **Step 1: Write the failing test**

```python
from fakeredis import FakeStrictRedis

from webhook_cursor_executor.models import DocumentSnapshot, RunResult
from webhook_cursor_executor.state_store import RedisStateStore


def test_event_seen_snapshot_and_run_result_roundtrip():
    redis_client = FakeStrictRedis(decode_responses=True)
    store = RedisStateStore(redis_client=redis_client)

    assert store.try_mark_event_seen("evt_1") is True
    assert store.try_mark_event_seen("evt_1") is False

    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_1",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path="C:\\workspaces\\pipeline",
        received_at="2026-04-26T10:00:00Z",
        version=3,
    )
    store.save_snapshot(snapshot)
    store.save_run_result(
        RunResult(
            run_id="run_1",
            document_id="doc_1",
            version=3,
            exit_code=0,
            status="succeeded",
            summary="ok",
        )
    )

    assert store.load_snapshot("doc_1").version == 3
    assert store.load_run_result("run_1").status == "succeeded"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_state_store.py -v`
Expected: FAIL with missing `state_store.py` or `RunResult`

- [ ] **Step 3: Write minimal implementation**

`webhook/src/webhook_cursor_executor/models.py`

```python
from __future__ import annotations

from pydantic import BaseModel


class DocumentSnapshot(BaseModel):
    event_id: str
    document_id: str
    folder_token: str
    event_type: str
    qa_rule_file: str
    dataset_id: str
    workspace_path: str
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
    qa_rule_file: str
    dataset_id: str
    workspace_path: str
    trigger_source: str
    received_at: str
    cursor_timeout_seconds: int
```

`webhook/src/webhook_cursor_executor/state_store.py`

```python
from __future__ import annotations

import time

from redis import Redis

from webhook_cursor_executor.models import DocumentSnapshot, RerunMarker, RunContext, RunResult


class RedisStateStore:
    def __init__(
        self,
        *,
        redis_client: Redis,
        event_seen_ttl_seconds: int = 86400,
        snapshot_ttl_seconds: int = 86400,
        rerun_ttl_seconds: int = 86400,
        run_context_ttl_seconds: int = 259200,
        run_result_ttl_seconds: int = 259200,
    ) -> None:
        self.redis = redis_client
        self.event_seen_ttl_seconds = event_seen_ttl_seconds
        self.snapshot_ttl_seconds = snapshot_ttl_seconds
        self.rerun_ttl_seconds = rerun_ttl_seconds
        self.run_context_ttl_seconds = run_context_ttl_seconds
        self.run_result_ttl_seconds = run_result_ttl_seconds

    def _event_seen_key(self, event_id: str) -> str:
        return f"webhook:event_seen:{event_id}"

    def _snapshot_key(self, document_id: str) -> str:
        return f"webhook:doc:snapshot:{document_id}"

    def _version_key(self, document_id: str) -> str:
        return f"webhook:doc:version:{document_id}"

    def _runlock_key(self, document_id: str) -> str:
        return f"webhook:doc:runlock:{document_id}"

    def _rerun_key(self, document_id: str) -> str:
        return f"webhook:doc:rerun:{document_id}"

    def _run_context_key(self, run_id: str) -> str:
        return f"webhook:run:context:{run_id}"

    def _run_result_key(self, run_id: str) -> str:
        return f"webhook:run:result:{run_id}"

    def try_mark_event_seen(self, event_id: str) -> bool:
        return bool(self.redis.set(self._event_seen_key(event_id), "1", nx=True, ex=self.event_seen_ttl_seconds))

    def next_version(self, document_id: str) -> int:
        value = int(self.redis.incr(self._version_key(document_id)))
        self.redis.expire(self._version_key(document_id), self.snapshot_ttl_seconds)
        return value

    def save_snapshot(self, snapshot: DocumentSnapshot) -> None:
        self.redis.set(self._snapshot_key(snapshot.document_id), snapshot.model_dump_json(), ex=self.snapshot_ttl_seconds)

    def load_snapshot(self, document_id: str) -> DocumentSnapshot | None:
        raw = self.redis.get(self._snapshot_key(document_id))
        return None if raw is None else DocumentSnapshot.model_validate_json(raw)

    def try_acquire_runlock(self, *, document_id: str, run_id: str, ttl_seconds: int) -> bool:
        return bool(self.redis.set(self._runlock_key(document_id), run_id, nx=True, ex=ttl_seconds))

    def runlock_owned_by(self, *, document_id: str, run_id: str) -> bool:
        return self.redis.get(self._runlock_key(document_id)) == run_id

    def release_runlock(self, *, document_id: str, run_id: str) -> None:
        if self.runlock_owned_by(document_id=document_id, run_id=run_id):
            self.redis.delete(self._runlock_key(document_id))

    def mark_rerun(self, *, document_id: str, target_version: int) -> None:
        marker = RerunMarker(target_version=target_version, updated_at=int(time.time()))
        self.redis.set(self._rerun_key(document_id), marker.model_dump_json(), ex=self.rerun_ttl_seconds)

    def get_rerun(self, document_id: str) -> RerunMarker | None:
        raw = self.redis.get(self._rerun_key(document_id))
        return None if raw is None else RerunMarker.model_validate_json(raw)

    def clear_rerun(self, document_id: str) -> None:
        self.redis.delete(self._rerun_key(document_id))

    def save_run_context(self, context: RunContext) -> None:
        self.redis.set(self._run_context_key(context.run_id), context.model_dump_json(), ex=self.run_context_ttl_seconds)

    def clear_run_context(self, run_id: str) -> None:
        self.redis.delete(self._run_context_key(run_id))

    def save_run_result(self, result: RunResult) -> None:
        self.redis.set(self._run_result_key(result.run_id), result.model_dump_json(), ex=self.run_result_ttl_seconds)

    def load_run_result(self, run_id: str) -> RunResult | None:
        raw = self.redis.get(self._run_result_key(run_id))
        return None if raw is None else RunResult.model_validate_json(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_state_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/src/webhook_cursor_executor/models.py webhook/src/webhook_cursor_executor/state_store.py webhook/tests/test_state_store.py
git commit -m "feat: add redis state store contracts"
```

### Task 3: Implement FastAPI Webhook App With Real Composition Root

**Files:**
- Create: `webhook/src/webhook_cursor_executor/app.py`
- Test: `webhook/tests/test_app.py`

- [ ] **Step 1: Write the failing test**

```python
from fakeredis import FakeStrictRedis
from fastapi.testclient import TestClient

from webhook_cursor_executor.app import create_app
from webhook_cursor_executor.settings import ExecutorSettings, RoutingConfig, PipelineWorkspace, FolderRoute
from webhook_cursor_executor.state_store import RedisStateStore


class FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))


def test_webhook_uses_redis_event_seen_and_enqueues_schedule():
    settings = ExecutorSettings(feishu_encrypt_key="")
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(path="C:\\workspaces\\pipeline", cursor_timeout_seconds=7200),
        folder_routes=[FolderRoute(folder_token="fld_team_a", qa_rule_file="rules/team_a_qa.md", dataset_id="dataset_team_a")],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(settings=settings, routing_config=routing, state_store=store, queue=queue)
    client = TestClient(app)

    payload = {
        "header": {"event_id": "evt_1", "event_type": "drive.file.updated_v1"},
        "event": {"document_id": "doc_1", "folder_token": "fld_team_a"},
    }

    first = client.post("/webhook/feishu", json=payload)
    second = client.post("/webhook/feishu", json=payload)

    assert first.status_code == 200
    assert second.json()["msg"] == "duplicate"
    assert queue.calls[0][0] == "schedule_document_job"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_app.py -v`
Expected: FAIL with missing `app.py`

- [ ] **Step 3: Write minimal implementation**

`webhook/src/webhook_cursor_executor/app.py`

```python
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis import Redis

from webhook_cursor_executor.models import DocumentSnapshot
from webhook_cursor_executor.settings import ExecutorSettings, FolderRoute, RoutingConfig, get_executor_settings, load_routing_config
from webhook_cursor_executor.state_store import RedisStateStore


def verify_signature(timestamp: str, nonce: str, encrypt_key: str, body: bytes, signature: str) -> bool:
    if not encrypt_key:
        return True
    digest = hashlib.sha256(f"{timestamp}{nonce}{encrypt_key}".encode("utf-8") + body).hexdigest()
    return digest == signature


def parse_request_body(encrypt_key: str, body: bytes) -> dict[str, Any]:
    data = json.loads(body.decode("utf-8"))
    if "encrypt" not in data or not encrypt_key:
        return data
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    raw = base64.b64decode(data["encrypt"])
    iv, ciphertext = raw[:16], raw[16:]
    plaintext = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext), AES.block_size)
    return json.loads(plaintext.decode("utf-8"))


def resolve_folder_route(routing_config: RoutingConfig, folder_token: str) -> FolderRoute | None:
    for route in routing_config.folder_routes:
        if route.folder_token == folder_token:
            return route
    return None


class InlineQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))


def create_app(*, settings: ExecutorSettings, routing_config: RoutingConfig, state_store: RedisStateStore, queue) -> FastAPI:
    app = FastAPI(title="Webhook Cursor Executor", version="0.1.0")

    @app.post(settings.feishu_webhook_path)
    async def feishu_webhook(request: Request) -> JSONResponse:
        raw = await request.body()
        payload = parse_request_body(settings.feishu_encrypt_key, raw)

        if payload.get("type") == "url_verification" and "challenge" in payload:
            return JSONResponse({"challenge": str(payload["challenge"])})

        timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        signature = request.headers.get("X-Lark-Signature", "")
        if not verify_signature(timestamp, nonce, settings.feishu_encrypt_key, raw, signature):
            return JSONResponse({"error": "invalid signature"}, status_code=401)

        header = payload.get("header") or {}
        event = payload.get("event") or {}
        event_id = str(header.get("event_id") or "").strip()
        event_type = str(header.get("event_type") or "").strip()
        document_id = str(event.get("document_id") or event.get("file_token") or "").strip()
        folder_token = str(event.get("folder_token") or "").strip()

        if not event_id or not document_id:
            return JSONResponse({"error": "missing event_id or document_id"}, status_code=400)
        if not state_store.try_mark_event_seen(event_id):
            return JSONResponse({"code": 0, "msg": "duplicate"})

        route = resolve_folder_route(routing_config, folder_token)
        if route is None:
            return JSONResponse({"error": "folder_route_not_resolved"}, status_code=400)

        version = state_store.next_version(document_id)
        snapshot = DocumentSnapshot(
            event_id=event_id,
            document_id=document_id,
            folder_token=folder_token,
            event_type=event_type,
            qa_rule_file=route.qa_rule_file,
            dataset_id=route.dataset_id,
            workspace_path=routing_config.pipeline_workspace.path,
            received_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            version=version,
        )
        state_store.save_snapshot(snapshot)
        queue.enqueue("schedule_document_job", document_id=document_id, version=version)
        return JSONResponse({"code": 0, "msg": "ok"})

    return app


def build_app() -> FastAPI:
    settings = get_executor_settings()
    routing_config = load_routing_config(settings)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    state_store = RedisStateStore(redis_client=redis_client)
    queue = InlineQueue()
    return create_app(settings=settings, routing_config=routing_config, state_store=state_store, queue=queue)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_app.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/src/webhook_cursor_executor/app.py webhook/tests/test_app.py
git commit -m "feat: add webhook app with redis idempotency"
```

### Task 4: Add Task Bundle Writer And Cursor Max Mode Fail-Fast

**Files:**
- Create: `webhook/src/webhook_cursor_executor/task_files.py`
- Create: `webhook/src/webhook_cursor_executor/cursor_cli.py`
- Test: `webhook/tests/test_task_files.py`
- Test: `webhook/tests/test_cursor_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
import json

from webhook_cursor_executor.task_files import write_task_bundle
from webhook_cursor_executor.cursor_cli import ensure_max_mode_config


def test_write_task_bundle_uses_run_dir(tmp_path):
    context = {
        "schema_version": "1",
        "run_id": "run_001",
        "event_id": "evt_1",
        "document_id": "doc_1",
        "folder_token": "fld_team_a",
        "event_type": "drive.file.updated_v1",
        "snapshot_version": 3,
        "qa_rule_file": "rules/team_a_qa.md",
        "dataset_id": "dataset_team_a",
        "workspace_path": str(tmp_path),
        "trigger_source": "feishu_webhook",
        "received_at": "2026-04-26T10:00:00Z",
        "cursor_timeout_seconds": 7200,
    }

    bundle = write_task_bundle(workspace_path=tmp_path, run_id="run_001", context=context)
    saved = json.loads(bundle.context_path.read_text(encoding="utf-8"))

    assert bundle.outputs_dir.is_dir()
    assert ".cursor_task/run_001" in str(bundle.context_path).replace("\\", "/")
    assert saved["dataset_id"] == "dataset_team_a"


def test_ensure_max_mode_config_creates_minimal_file(tmp_path):
    config_path = tmp_path / "cli-config.json"
    ensure_max_mode_config(config_path=config_path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["maxMode"] is True
    assert payload["model"]["maxMode"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_task_files.py tests/test_cursor_cli.py -v`
Expected: FAIL with missing modules

- [ ] **Step 3: Write minimal implementation**

`webhook/src/webhook_cursor_executor/task_files.py`

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TaskBundlePaths:
    run_dir: Path
    prompt_path: Path
    context_path: Path
    outputs_dir: Path


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
- `dataset_id` 必须以 `task_context.json` 中的显式注入值为准。
- 最终结果需要上传到 `task_context.json` 中指定的 Dify `dataset_id`。
"""


def write_task_bundle(*, workspace_path: Path, run_id: str, context: dict[str, Any]) -> TaskBundlePaths:
    run_dir = workspace_path / ".cursor_task" / run_id
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = run_dir / "task_prompt.md"
    context_path = run_dir / "task_context.json"
    prompt_path.write_text(build_task_prompt(context), encoding="utf-8")
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    return TaskBundlePaths(run_dir=run_dir, prompt_path=prompt_path, context_path=context_path, outputs_dir=outputs_dir)
```

`webhook/src/webhook_cursor_executor/cursor_cli.py`

```python
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CursorRunResult:
    exit_code: int
    status: str
    summary: str


def ensure_max_mode_config(*, config_path: Path) -> None:
    payload: dict = {}
    if config_path.exists():
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["maxMode"] = True
    model = payload.get("model") or {}
    model["maxMode"] = True
    payload["model"] = model
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def launch_cursor_agent(*, command: str, cwd: Path, prompt_text: str, model: str, timeout_seconds: int) -> CursorRunResult:
    completed = subprocess.run(
        [command, "agent", "--model", model, prompt_text],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return CursorRunResult(
        exit_code=completed.returncode,
        status="succeeded" if completed.returncode == 0 else "failed",
        summary=completed.stdout.strip() or completed.stderr.strip(),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_task_files.py tests/test_cursor_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/src/webhook_cursor_executor/task_files.py webhook/src/webhook_cursor_executor/cursor_cli.py webhook/tests/test_task_files.py webhook/tests/test_cursor_cli.py
git commit -m "feat: add task bundle and cursor cli sync"
```

### Task 5: Implement Scheduler And Real RQ Worker Entry Points

**Files:**
- Create: `webhook/src/webhook_cursor_executor/scheduler.py`
- Create: `webhook/src/webhook_cursor_executor/worker.py`
- Test: `webhook/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing tests**

```python
from fakeredis import FakeStrictRedis

from webhook_cursor_executor.models import DocumentSnapshot
from webhook_cursor_executor.scheduler import finalize_document_run_job, schedule_document_job
from webhook_cursor_executor.state_store import RedisStateStore


class FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))


def test_schedule_marks_rerun_when_busy():
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_1",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path="C:\\workspaces\\pipeline",
        received_at="2026-04-26T10:00:00Z",
        version=2,
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(document_id="doc_1", run_id="run_existing", ttl_seconds=10800)

    schedule_document_job(document_id="doc_1", version=2, state_store=store, queue=queue, runlock_ttl_seconds=10800)

    assert store.get_rerun("doc_1").target_version == 2
    assert queue.calls == []


def test_finalize_saves_result_and_requeues_newer_version():
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_1",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path="C:\\workspaces\\pipeline",
        received_at="2026-04-26T10:00:00Z",
        version=5,
    )
    store.save_snapshot(snapshot)
    store.mark_rerun(document_id="doc_1", target_version=6)

    finalize_document_run_job(
        run_id="run_1",
        document_id="doc_1",
        version=5,
        exit_code=0,
        status="succeeded",
        summary="ok",
        state_store=store,
        queue=queue,
    )

    assert store.load_run_result("run_1").status == "succeeded"
    assert queue.calls == [("schedule_document_job", {"document_id": "doc_1", "version": 5})]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_scheduler.py -v`
Expected: FAIL with missing scheduler functions

- [ ] **Step 3: Write minimal implementation**

`webhook/src/webhook_cursor_executor/scheduler.py`

```python
from __future__ import annotations

import uuid
from pathlib import Path

from webhook_cursor_executor.cursor_cli import ensure_max_mode_config, launch_cursor_agent
from webhook_cursor_executor.models import RunContext, RunResult, TaskContext
from webhook_cursor_executor.task_files import write_task_bundle


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


def schedule_document_job(*, document_id: str, version: int, state_store, queue, runlock_ttl_seconds: int) -> None:
    snapshot = state_store.load_snapshot(document_id)
    if snapshot is None or snapshot.version != version:
        return

    run_id = new_run_id()
    locked = state_store.try_acquire_runlock(document_id=document_id, run_id=run_id, ttl_seconds=runlock_ttl_seconds)
    if not locked:
        state_store.mark_rerun(document_id=document_id, target_version=snapshot.version)
        return

    queue.enqueue("launch_cursor_run_job", document_id=document_id, version=snapshot.version, run_id=run_id)



def launch_cursor_run_job(*, document_id: str, version: int, run_id: str, state_store, queue, settings) -> None:
    snapshot = state_store.load_snapshot(document_id)
    if snapshot is None or snapshot.version != version:
        finalize_document_run_job(
            run_id=run_id,
            document_id=document_id,
            version=version,
            exit_code=1,
            status="failed",
            summary="snapshot_missing_or_stale",
            state_store=state_store,
            queue=queue,
        )
        return
    if not state_store.runlock_owned_by(document_id=document_id, run_id=run_id):
        return

    task_context = TaskContext(
        schema_version="1",
        run_id=run_id,
        event_id=snapshot.event_id,
        document_id=snapshot.document_id,
        folder_token=snapshot.folder_token,
        event_type=snapshot.event_type,
        snapshot_version=snapshot.version,
        qa_rule_file=snapshot.qa_rule_file,
        dataset_id=snapshot.dataset_id,
        workspace_path=snapshot.workspace_path,
        trigger_source="feishu_webhook",
        received_at=snapshot.received_at,
        cursor_timeout_seconds=settings.cursor_run_timeout_seconds,
    )
    bundle = write_task_bundle(
        workspace_path=Path(snapshot.workspace_path),
        run_id=run_id,
        context=task_context.model_dump(),
    )

    state_store.save_run_context(
        RunContext(
            run_id=run_id,
            document_id=document_id,
            version=version,
            event_id=snapshot.event_id,
            workspace_path=snapshot.workspace_path,
            status="running",
        )
    )

    try:
        ensure_max_mode_config(config_path=Path(settings.cursor_cli_config_path))
    except Exception as exc:
        finalize_document_run_job(
            run_id=run_id,
            document_id=document_id,
            version=version,
            exit_code=1,
            status="failed",
            summary=f"max_mode_sync_failed:{exc}",
            state_store=state_store,
            queue=queue,
        )
        return

    result = launch_cursor_agent(
        command=settings.cursor_cli_command,
        cwd=Path(snapshot.workspace_path),
        prompt_text=bundle.prompt_path.read_text(encoding="utf-8"),
        model=settings.cursor_cli_model,
        timeout_seconds=settings.cursor_run_timeout_seconds,
    )
    queue.enqueue(
        "finalize_document_run_job",
        run_id=run_id,
        document_id=document_id,
        version=version,
        exit_code=result.exit_code,
        status=result.status,
        summary=result.summary,
    )



def finalize_document_run_job(*, run_id: str, document_id: str, version: int, exit_code: int, status: str, summary: str | None, state_store, queue) -> None:
    state_store.save_run_result(
        RunResult(
            run_id=run_id,
            document_id=document_id,
            version=version,
            exit_code=exit_code,
            status=status,
            summary=summary,
        )
    )
    state_store.clear_run_context(run_id)
    state_store.release_runlock(document_id=document_id, run_id=run_id)

    rerun = state_store.get_rerun(document_id)
    latest_snapshot = state_store.load_snapshot(document_id)
    if rerun is None or latest_snapshot is None:
        state_store.clear_rerun(document_id)
        return
    if rerun.target_version <= version:
        state_store.clear_rerun(document_id)
        return

    state_store.clear_rerun(document_id)
    queue.enqueue("schedule_document_job", document_id=document_id, version=latest_snapshot.version)
```

`webhook/src/webhook_cursor_executor/worker.py`

```python
from __future__ import annotations

from redis import Redis
from rq import Queue

from webhook_cursor_executor.scheduler import finalize_document_run_job, launch_cursor_run_job, schedule_document_job
from webhook_cursor_executor.settings import get_executor_settings
from webhook_cursor_executor.state_store import RedisStateStore


class RQQueueAdapter:
    def __init__(self, *, queue: Queue) -> None:
        self.queue = queue

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.queue.enqueue(
            f"webhook_cursor_executor.worker.{job_name}_entry",
            kwargs=kwargs,
        )


def build_worker_runtime():
    settings = get_executor_settings()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    store = RedisStateStore(redis_client=redis_client)
    queue = RQQueueAdapter(queue=Queue(settings.vla_queue_name, connection=redis_client))
    return settings, store, queue



def schedule_document_job_entry(*, document_id: str, version: int) -> None:
    settings, store, queue = build_worker_runtime()
    schedule_document_job(
        document_id=document_id,
        version=version,
        state_store=store,
        queue=queue,
        runlock_ttl_seconds=settings.doc_runlock_ttl_seconds,
    )



def launch_cursor_run_job_entry(*, document_id: str, version: int, run_id: str) -> None:
    settings, store, queue = build_worker_runtime()
    launch_cursor_run_job(
        document_id=document_id,
        version=version,
        run_id=run_id,
        state_store=store,
        queue=queue,
        settings=settings,
    )



def finalize_document_run_job_entry(*, run_id: str, document_id: str, version: int, exit_code: int, status: str, summary: str | None = None) -> None:
    _, store, queue = build_worker_runtime()
    finalize_document_run_job(
        run_id=run_id,
        document_id=document_id,
        version=version,
        exit_code=exit_code,
        status=status,
        summary=summary,
        state_store=store,
        queue=queue,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/src/webhook_cursor_executor/scheduler.py webhook/src/webhook_cursor_executor/worker.py webhook/tests/test_scheduler.py
git commit -m "feat: add scheduler and rq worker runtime"
```

### Task 6: Add Focused End-To-End Verification And Remove Low-Value Gaps

**Files:**
- Modify: `webhook/tests/test_app.py`
- Modify: `webhook/tests/test_scheduler.py`
- Modify: `webhook/README.md`

- [ ] **Step 1: Write the missing focused tests**

```python
def test_url_verification_returns_challenge(client_factory):
    client = client_factory()
    response = client.post("/webhook/feishu", json={"type": "url_verification", "challenge": "abc"})
    assert response.status_code == 200
    assert response.json() == {"challenge": "abc"}
```

```python
def test_launch_fails_fast_when_max_mode_sync_fails(monkeypatch, fake_state_store, fake_queue, settings_obj):
    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.ensure_max_mode_config",
        lambda **_: (_ for _ in ()).throw(OSError("locked")),
    )

    launch_cursor_run_job(
        document_id="doc_1",
        version=1,
        run_id="run_1",
        state_store=fake_state_store,
        queue=fake_queue,
        settings=settings_obj,
    )

    assert fake_state_store.load_run_result("run_1").status == "failed"
```

- [ ] **Step 2: Run the focused suite**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_settings.py tests/test_state_store.py tests/test_task_files.py tests/test_cursor_cli.py tests/test_app.py tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 3: Update README startup section**

`webhook/README.md`

```md
## Local bootstrap

```powershell
cd c:\WorkPlace\NewVLA\webhook
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[test]
.\.venv\Scripts\python.exe -m pytest tests -v
```

## Runtime entrypoints

- HTTP app: `webhook_cursor_executor.app:build_app`
- RQ jobs:
  - `webhook_cursor_executor.worker.schedule_document_job_entry`
  - `webhook_cursor_executor.worker.launch_cursor_run_job_entry`
  - `webhook_cursor_executor.worker.finalize_document_run_job_entry`
```

- [ ] **Step 4: Re-run the focused suite**

Run: `cd webhook; .\.venv\Scripts\python.exe -m pytest tests/test_settings.py tests/test_state_store.py tests/test_task_files.py tests/test_cursor_cli.py tests/test_app.py tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/tests/test_app.py webhook/tests/test_scheduler.py webhook/README.md
git commit -m "feat: complete webhook executor v1 plan"
```

## Self-Review

### Spec Coverage

- `event_id` 幂等：Task 2 的 `try_mark_event_seen()` + Task 3 的 webhook 测试覆盖。
- `document_id` snapshot/version/runlock/rerun：Task 2、Task 5 覆盖。
- `finalize` 写运行结果：Task 2、Task 5 覆盖。
- challenge / 验签 / 解密：Task 3、Task 6 覆盖。
- 单 workspace + `folder_token` 路由：Task 1、Task 3 覆盖。
- `.cursor_task/{run_id}` 注入目录：Task 4 覆盖。
- Max Mode 同步且失败即终止：Task 4、Task 6 覆盖。
- `schedule / launch / finalize` 三段式任务：Task 5 覆盖。
- 可运行装配入口：Task 3 的 `build_app()`、Task 5 的 `build_worker_runtime()` 覆盖。

### Gaps Check

- 不写运行日志文件落盘；这不是 spec v1 必需项。
- 不做 runlock 心跳；spec 明确 v1 不需要。
- 不做 `queue.py` / `jobs.py` 包装层；这是刻意减法，不是遗漏。

### Placeholder Scan

- 已去掉 `queue.py`、`jobs.py`、`test_jobs.py` 这类低价值壳层。
- 已补回 Redis 幂等、run result、真实 app / worker 装配、Max Mode fail-fast。
- 计划里的测试都直接指向高风险路径，不再把 `ModuleNotFoundError` 当主要价值。

Plan complete and saved to `docs/superpowers/plans/2026-04-26-webhook-cursor-executor-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
