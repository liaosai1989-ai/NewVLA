# task_context / Bootstrap 样例 / Agent 阅读合同 Implementation Plan

> **落地状态：已落地**（2026-04-28；实现见 `webhook/`、`dify_upload/`、`bootstrap/`、`prompts/`、`docs/superpowers/samples/`；合同 spec 与本文成对更新。）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单次合并批次内落地 [2026-04-28-task-context-bootstrap-sample-agent-contract-design.md](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) 全文合同：`.env` 文件夹路由真源、`dify_target_key` / `ingest_kind` 贯通快照与 `task_context.json`、Redis 旧数据策略、`resolve_dify_target` 薄封装、`prompts/AGENTS.txt` §10 一次合并、bootstrap `doctor`/README/样例 JSON、§2.3 占位干跑闭合；`pytest` 全绿。

**Architecture:** webhook `load_routing_config` 双分支（`FEISHU_FOLDER_ROUTE_KEYS` 非空 → 从 `.env` 构造 `RoutingConfig`；否则 JSON 回退 + 警告）。`DocumentSnapshot` / `TaskContext` 扩展字段；HTTP → RQ 显式传 `ingest_kind`（禁止 worker 单靠 `document_id` 反推）。`dify_upload` 内新增单函数读 `task_context` + 工作区 `.env` → `DifyTargetConfig`（不读 JSON 文件的职责仍在封装层，模块边界与 spec §8.4 一致）。反过度设计：不引入新包、不建抽象层目录树；Redis 策略在 PR 内选定**一条**并写进 `webhook/操作手册.md`。**不降级**：§3 必填（含 bootstrap 演示 `ingest_kind`、占位 `dify_target_key`）、§8.2 代码合入、§2.3 `dataset_id_is_placeholder` **或** 等价显式文案路径二选一且须在单测中断言。

**Tech Stack:** Python 3.12+、Pydantic v2、FastAPI、RQ、Redis、`python-dotenv`（webhook 显式依赖）、现有 `dify_upload` / `feishu_fetch` / `bootstrap` / `onboard.env_contract`。

---

## 跨 plan 合并与联动（code-reviewer 收口）

1. **`settings.py` 单窗口串改（高优先级）**  
   [2026-04-28-production-bootstrap-deployment-implementation-plan.md](./2026-04-28-production-bootstrap-deployment-implementation-plan.md) **Task 12**（`_env_file()`、`DotEnvSettingsSource`、`test_env_file_uses_vla_workspace_root`）与 **本 plan Task 2**（`load_routing_config`、`.env`/JSON 分支、`FolderRoute.dify_target_key`）**触碰同一文件**。须 **同一合并批次、prefer 单作者串行**：先合 Task 12 基底，再叠 Task 2；**禁止**两路并行 PR 各改一半 `webhook/src/webhook_cursor_executor/settings.py`。production plan 顶部 **修订说明** 已写此条。

2. **`FEISHU_FOLDER_<KEY>_NAME` 与 `feishu_folder_group_keys`（高优先级）**  
   `onboard/src/feishu_onboard/env_contract.py` 中 `feishu_folder_group_keys` 含 **`FEISHU_FOLDER_<KEY>_NAME`**。**本批次锁死：五键同质** — webhook `.env` 路由、`doctor`、onboard **同一键集**（`NAME`、`TOKEN`、`DIFY_TARGET_KEY`、`DATASET_ID`、`QA_RULE_FILE` 均非空方通过）。单测与 `.env.example` / 样本 env **须含 `NAME`**。**禁止**「四键必填 + `NAME` 可选」或 webhook 不消费 `NAME` 分叉。

3. **样本 env 与联调脚本（中优先级）**  
   `docs/superpowers/samples/pipeline-workspace-root.env.example` 须增补 **`FEISHU_FOLDER_ROUTE_KEYS` + 示例 route 组**（含 `NAME`），与 §7 `.env` 真源一致；`test_tool/start_temp_feishu_tunnel.ps1` 及 [2026-04-26-cloudflare-temp-tunnel-webhook.md](./2026-04-26-cloudflare-temp-tunnel-webhook.md) 由 **Task 7** 自检 + 该 plan **顶部修订说明** 指向 `.env` 优先，避免联调仍只教 JSON。

4. **`ThirdParty.md` / `ENV-OLD-TO-NEW.md`**  
   **唯一落地步骤见 Task 11**（本处不重复条款，避免两处各改）。

5. **Plan 落地后（非本正文步骤、仓库规则）**  
   `NiceToHave.md` 总表、`plan-landed-renew-agents-rules.mdc`：`prompts/rules/**` 与 `sample_qa.md` 物化后 renew。

---

## 文件结构（落地前锁定）

| 路径 | 职责 |
|------|------|
| `webhook/pyproject.toml` | 增加 `python-dotenv` 依赖 |
| `webhook/src/webhook_cursor_executor/settings.py` | `FolderRoute.dify_target_key`；`load_routing_config` `.env`/JSON 分支；`pipeline_workspace` 按 spec §7.1 |
| `webhook/src/webhook_cursor_executor/models.py` | `DocumentSnapshot` / `TaskContext` 新字段 |
| `webhook/src/webhook_cursor_executor/state_store.py` | 旧快照缺键加载策略（与 §7.6 一致） |
| `webhook/src/webhook_cursor_executor/feishu_folder_resolve.py` | 路由命中与错误消息覆盖新字段 |
| `webhook/src/webhook_cursor_executor/app.py` | 写快照：`dify_target_key`、`ingest_kind`；RQ 入参含 `ingest_kind` |
| `webhook/src/webhook_cursor_executor/worker.py` | 对齐 RQ 契约；构造快照字段 |
| `webhook/src/webhook_cursor_executor/scheduler.py` | `TaskContext(...)` 补全字段 |
| `webhook/src/webhook_cursor_executor/task_files.py` | `build_task_prompt` 补 `dify_target_key` 句；占位干跑与 §2.3 对齐 |
| `webhook/config/folder_routes.example.json` | 每条 route 含 `dify_target_key` |
| `webhook/tests/*.py` | 枚举更新（见各 Task） |
| `dify_upload/src/dify_upload/resolve_target.py`（新） | `resolve_dify_target(...)` |
| `dify_upload/src/dify_upload/__init__.py` | export 新符号 |
| `dify_upload/tests/test_resolve_target.py`（新） | 封装单测 |
| `prompts/AGENTS.txt` | §10 表 5 行一次合并 |
| `prompts/rules/sample_qa.md`（新，若尚无） | 演示 QA；materialize 分发 |
| `docs/superpowers/samples/task_context.bootstrap.example.json`（新） | bootstrap 演示 JSON（含 `ingest_kind`、`dify_target_key`、`dataset_id_is_placeholder`） |
| `bootstrap/src/bootstrap/doctor.py` | `.env` 路由完整性检查；legacy JSON 警告路径保留 |
| `bootstrap/src/bootstrap/materialize.py`（或等价） | 确保样例规则与可选样例 JSON 路径在 README 可指 |
| `bootstrap/src/bootstrap/env_dotenv.py` | `read_env_keys`；doctor / 单测依赖，Task 10 改 doctor 时一并验证 |
| `bootstrap/src/bootstrap/routing_json.py` | `load_pipeline_workspace_path_from_json`；legacy WARNING 分支与 Task 10 一致 |
| `bootstrap/tests/test_env_dotenv.py` | 增补 `FEISHU_FOLDER_ROUTE_KEYS` 场景或文档化覆盖范围 |
| `bootstrap/src/bootstrap/interactive_setup.py` | stdout 提示与 BUG-005 / 路由真源口径对齐 §7，避免仍强调「仅 JSON 双写」 |
| `docs/superpowers/samples/pipeline-workspace-root.env.example` | 增补 `FEISHU_FOLDER_ROUTE_KEYS` + 示例 `FEISHU_FOLDER_<KEY>_*` 五键（含 `NAME`）与 `DIFY_TARGET_*` 指针 |
| `test_tool/start_temp_feishu_tunnel.ps1`（若存在） | Task 7：联调说明与 `.env` 路由优先一致 |
| `ThirdParty.md`、`ENV-OLD-TO-NEW.md` | **`python-dotenv` 登记**与**姊妹迁移叙事**均在 **Task 11** |
| `feishu_fetch/README.md` | `ingest_kind` 真源表述（Task 11 同批） |
| `.env.example`、`webhook/操作手册.md`、`webhook/阶段性验收手册.md`、`BugList.md`、姊妹 design 修订说明 | 与 spec §7.2–§7.3、§9 同步 |

---

### Task 1: `DocumentSnapshot` / `TaskContext` 模型扩展

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/models.py`
- Test: `webhook/tests/test_models.py`（若无则新建）

- [ ] **Step 1: 写失败单测（缺 `ingest_kind` 时生产路径期望）**

```python
# webhook/tests/test_models.py
import pytest
from pydantic import ValidationError
from webhook_cursor_executor.models import DocumentSnapshot, TaskContext


def test_document_snapshot_allows_default_dify_target_for_legacy_json():
    s = DocumentSnapshot.model_validate(
        {
            "event_id": "e1",
            "document_id": "d1",
            "folder_token": "f1",
            "event_type": "drive.file.edit_v1",
            "qa_rule_file": "rules/a.md",
            "dataset_id": "ds",
            "workspace_path": "C:\\ws",
            "cursor_timeout_seconds": 7200,
            "received_at": "2026-04-28T00:00:00+00:00",
            "version": 1,
            "ingest_kind": "drive_file",
        }
    )
    assert s.dify_target_key == "DEFAULT"


def test_task_context_requires_ingest_kind_and_dify_target_key():
    base = dict(
        schema_version="1",
        run_id="run_x",
        event_id="e1",
        document_id="d1",
        folder_token="f1",
        event_type="drive.file.edit_v1",
        snapshot_version=1,
        qa_rule_file="rules/a.md",
        dataset_id="ds",
        workspace_path="C:\\ws",
        trigger_source="feishu_webhook",
        received_at="2026-04-28T00:00:00+00:00",
        cursor_timeout_seconds=7200,
        ingest_kind="drive_file",
        dify_target_key="DEFAULT",
    )
    TaskContext.model_validate({**base, "dataset_id_is_placeholder": False})
    bad = {k: v for k, v in base.items() if k != "ingest_kind"}
    with pytest.raises(ValidationError):
        TaskContext.model_validate(bad)
```

- [ ] **Step 2: 运行确认失败**

Run: `cd webhook; pytest tests/test_models.py -v`

Expected: `ValidationError` 或 `model_validate` 行为与改前不一致导致失败（若模型尚未改，先 expect 收集失败原因再改 Step 3）。

- [ ] **Step 3: 最小实现**

在 `models.py`：

- `DocumentSnapshot` 增加：`dify_target_key: str = "DEFAULT"`；`ingest_kind: str`（**无默认值**；新快照由写入方必填。**禁止**在 `state_store` 之外为 Redis 旧数据静默填 `ingest_kind`。缺键旧快照拒载见 Task 4）。
- `TaskContext` 增加：`dify_target_key: str`；`ingest_kind: str`；`dataset_id_is_placeholder: bool = False`。

（若 Pydantic 版本需 `Field` 描述，可加；勿加无关 validator。）

- [ ] **Step 4: 运行通过**

Run: `cd webhook; pytest tests/test_models.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webhook/src/webhook_cursor_executor/models.py webhook/tests/test_models.py
git commit -m "feat(webhook): TaskContext ingest_kind and dify_target_key fields"
```

---

### Task 2: `settings.py` — `FolderRoute` 与 `load_routing_config` 双分支

**Files:**
- Modify: `webhook/pyproject.toml`
- Modify: `webhook/src/webhook_cursor_executor/settings.py`
- Test: `webhook/tests/test_settings.py`

- [ ] **Step 1: 依赖**

在 `webhook/pyproject.toml` 的 `dependencies` 增加：`"python-dotenv>=1.0,<2.0"`。

- [ ] **Step 2: 失败单测 — `.env` 路由优先**

```python
# webhook/tests/test_settings.py 内新增
import os
from pathlib import Path
import json
import pytest
from webhook_cursor_executor.settings import ExecutorSettings, load_routing_config


def test_load_routing_from_env_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    ws = tmp_path / "ws"
    ws.mkdir()
    env_file.write_text(
        "\n".join(
            [
                f"VLA_WORKSPACE_ROOT={ws}",
                "FEISHU_FOLDER_ROUTE_KEYS=MAIN",
                "FEISHU_FOLDER_MAIN_NAME=main-route",
                "FEISHU_FOLDER_MAIN_TOKEN=ftok",
                "FEISHU_FOLDER_MAIN_QA_RULE_FILE=rules/q.md",
                "FEISHU_FOLDER_MAIN_DATASET_ID=ds1",
                "FEISHU_FOLDER_MAIN_DIFY_TARGET_KEY=DEFAULT",
                "CURSOR_RUN_TIMEOUT_SECONDS=3600",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("VLA_WORKSPACE_ROOT", str(ws))
    # 指向空 JSON 或无效 JSON 的路径应仍成功：真源为 .env
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("FOLDER_ROUTES_FILE", str(bad_json))
    settings = ExecutorSettings()
    cfg = load_routing_config(settings)
    assert len(cfg.folder_routes) == 1
    assert cfg.folder_routes[0].dify_target_key == "DEFAULT"
    assert cfg.pipeline_workspace.path == str(ws.resolve())
    assert cfg.pipeline_workspace.cursor_timeout_seconds == 3600
```

- [ ] **Step 3: 运行失败**

Run: `cd webhook; pytest tests/test_settings.py::test_load_routing_from_env_keys -v`

Expected: FAIL（函数未实现或行为不符）

- [ ] **Step 4: 实现要点**

1. `FolderRoute` 增加 `dify_target_key: str = "DEFAULT"`（JSON 回退缺键兼容）。
2. 新增函数例如 `_routing_from_env(settings: ExecutorSettings) -> RoutingConfig | None`：读 `_env_file()`，用 `dotenv_values` + **进程 `os.environ` 覆盖**（与 spec 一致）；解析 `FEISHU_FOLDER_ROUTE_KEYS`（逗号分隔、`strip`、`upper`）；每组键与 `onboard/src/feishu_onboard/env_contract.py` 中 `feishu_folder_group_keys` **一致**（实现 PR 内对照或抽共享常量，**禁止**两处手写漂移）。
3. `load_routing_config(settings)`：若 `FEISHU_FOLDER_ROUTE_KEYS` 非空（strip 后）→ 返回 `_routing_from_env`；否则 `json.loads(Path(settings.folder_routes_file).read_text(...))` 并 **logging.warning** 遗留路径。
4. `pipeline_workspace.path`：`VLA_WORKSPACE_ROOT` 已设则其规范化绝对路径；否则为 `_env_file().parent.resolve()` 字符串形式。
5. `cursor_timeout_seconds`：`settings.cursor_run_timeout_seconds`。
6. `.env` 模式缺 **`feishu_folder_group_keys(route_key)` 所列任一键（含 `NAME`，五键同质）** → `ValueError` 信息含 route key（与跨 plan §2、`doctor` 同源，**无二义分叉**）。

注意：`get_executor_settings` 已 `@lru_cache`；路由仅随 `.env` 变时，现有测试若依赖 monkeypatch，须在测试中 `get_executor_settings.cache_clear()`（如已有模式则沿用）。**与 production-bootstrap Task 12 同文件**：见上文 **跨 plan 合并**。

- [ ] **Step 5: 补测 JSON 回退**

单测：未设 `FEISHU_FOLDER_ROUTE_KEYS` 时仍从 `folder_routes_file` 加载；且 JSON 内每条含 `dify_target_key`。

- [ ] **Step 6: 全量 webhook pytest**

Run: `cd webhook; pytest -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add webhook/pyproject.toml webhook/src/webhook_cursor_executor/settings.py webhook/tests/test_settings.py
git commit -m "feat(webhook): load folder routes from .env with JSON fallback"
```

---

### Task 3: `feishu_folder_resolve` 与 `folder_routes.example.json`

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/feishu_folder_resolve.py`
- Modify: `webhook/config/folder_routes.example.json`
- Test: `webhook/tests/test_feishu_folder_resolve.py`

- [ ] **Step 1: 更新 example JSON**  
  每条 `folder_routes[]` 增加 `"dify_target_key": "DEFAULT"`（或示例 key）。

- [ ] **Step 2: 单测**  
  覆盖：命中路由含 `dify_target_key`；token 未命中错误消息仍清晰。

- [ ] **Step 3: 实现**  
  仅随 `FolderRoute` 字段调整访问处；无额外抽象。

- [ ] **Step 4: `cd webhook; pytest`**

- [ ] **Step 5: Commit**  
  `git commit -m "chore(webhook): folder route example and resolve for dify_target_key"`

---

### Task 4: `state_store` — Redis 旧快照 §7.6

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/state_store.py`
- Test: `webhook/tests/test_state_store.py`

**选定策略（本 plan 写死，避免静默错 ingest）：** 从 Redis 读出 JSON 后，若缺 **`ingest_kind`** → **拒绝加载**（`load_snapshot` 返回 `None` 或记录 error 日志并返回 `None`，与 `app`/`scheduler`「无快照」分支一致）；缺 **`dify_target_key`** 可 **仅在校验前** 注入 `"DEFAULT"` 再 `model_validate`（与 `DocumentSnapshot` 默认一致）。**禁止**为 `ingest_kind` 填默认 `cloud_docx`/`drive_file`。

**spec §7.6 对照：** 采用 **（b）类** — 缺 `ingest_kind` 拒绝；`dify_target_key` 允许按上条注入 `DEFAULT`。**不**另写完整（a）清库-only /（c）-only 长文；运维清库、升快照版本句落在 **`webhook/操作手册.md`**（与 Task 7 同批）。

- [ ] **Step 1: 单测**  
  写入旧格式 JSON（无 `ingest_kind`）→ 断言加载失败或 `None`；有新字段 → 成功。

- [ ] **Step 2: 实现**  
  在反序列化路径集中处理。

- [ ] **Step 3: `cd webhook; pytest tests/test_state_store.py -v`**

- [ ] **Step 4: Commit**  
  `git commit -m "fix(webhook): reject Redis snapshots missing ingest_kind"`

---

### Task 5: `ingest_kind` 推导、`app.py`、`worker.py`、RQ 契约

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/app.py`
- Modify: `webhook/src/webhook_cursor_executor/worker.py`
- Test: `webhook/tests/test_app.py`、`webhook/tests/test_worker_ingest.py`

**推导规则（与 [2026-04-26-webhook-cursor-executor-design.md](../specs/2026-04-26-webhook-cursor-executor-design.md) 修订表一致，实现时以该文为准）：** 在事件解析与 `folder_token` 路由完成后，根据事件类型 / 对象类型映射到 `cloud_docx` | `drive_file`。抽 **单一纯函数** `derive_ingest_kind(event: dict, header: dict) -> str` 于 `app.py` 同包新模块 `ingest_kind.py` **或** `app.py` 内顶层函数（仅一处真相，禁止 `app`/`worker` 复制粘贴分叉逻辑）。

- [ ] **Step 1: 单测 `derive_ingest_kind`**  
  至少 2 例：`cloud_docx` 与 `drive_file` 各一；边界：缺字段时 `ValueError` 或明确 HTTP 4xx（与现网一致）。

- [ ] **Step 2: `app.py`**  
  构造 `DocumentSnapshot` 时设置 `ingest_kind=`、`dify_target_key=route.dify_target_key`；入队 `ingest_feishu_document_event` 时 **`ingest_kind` 作为 RQ kwargs**。

- [ ] **Step 3: `worker.py`**  
  `ingest_feishu_document_event_entry` 使用入参 `ingest_kind` 写快照；**禁止**忽略入参自行推导（可断言入参与 event 一致性的 debug 日志可选）。

- [ ] **Step 4: 无 `folder_token` 路径**  
  与 spec §7 一致：凡能进入写快照的路径必须带 `ingest_kind`。

- [ ] **Step 5: `cd webhook; pytest tests/test_app.py tests/test_worker_ingest.py -v`**

- [ ] **Step 6: Commit**  
  `git commit -m "feat(webhook): pass ingest_kind through RQ and snapshot"`

---

### Task 6: `scheduler.py` 与 `task_files.build_task_prompt`

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/scheduler.py`
- Modify: `webhook/src/webhook_cursor_executor/task_files.py`
- Test: `webhook/tests/test_scheduler.py`、`webhook/tests/test_task_files.py`

- [ ] **Step 1: `scheduler.py`**  
  `TaskContext(..., dify_target_key=snapshot.dify_target_key, ingest_kind=snapshot.ingest_kind, dataset_id_is_placeholder=...)`。  
  `dataset_id_is_placeholder`：在 scheduler 或 snapshot 写入阶段根据占位规则设置（推荐常量 `PLACEHOLDER_DATASET_IDS = frozenset({...})` 或前缀函数，单测覆盖）。

- [ ] **Step 2: `build_task_prompt`**  
  增加简短句：`dify_target_key` 以 `task_context.json` 为准，与 `.env` 中 `DIFY_TARGET_<KEY>_*` 经封装解析；`ingest_kind` 以 JSON 为准。  
  与 §2.3 一致：若干 `dataset_id` 或 `dataset_id_is_placeholder` 时明确「只生成校验 CSV、不上传」。

- [ ] **Step 3: 单测更新**  
  `test_scheduler.py` 断言落盘 JSON 含 `dify_target_key`、`ingest_kind`、`dataset_id_is_placeholder`。  
  `test_task_files.py` 断言新句存在。

- [ ] **Step 4: `cd webhook; pytest`**

- [ ] **Step 5: Commit**  
  `git commit -m "feat(webhook): task_context.json fields and task_prompt alignment"`

---

### Task 7: 其余 webhook 测试与文档登记

**Files:**
- Modify: `webhook/tests/test_cursor_cli.py`（若引用 `TaskContext` 构造）
- Modify: `webhook/操作手册.md`、`webhook/阶段性验收手册.md`
- Modify: `.env.example`（`FEISHU_FOLDER_ROUTE_KEYS` + 示例组键含 **`FEISHU_FOLDER_<KEY>_NAME`**）
- Modify: `BugList.md`（BUG-004/005 关单条件）
- Modify: [2026-04-26-webhook-cursor-executor-design.md](../specs/2026-04-26-webhook-cursor-executor-design.md) 顶部落地后修订说明（本 Task 与代码同 PR）
- Modify: `test_tool/start_temp_feishu_tunnel.ps1`（若脚本内仍仅强调 `FOLDER_ROUTES_FILE` / JSON，改为 **`.env` 路由优先** + JSON legacy 一句）

- [ ] **Step 1: `cd webhook; pytest` 全绿**

- [ ] **Step 2: 手册与 `.env.example`**  
  第四步改为优先 `FEISHU_FOLDER_ROUTE_KEYS`；`FOLDER_ROUTES_FILE` 注释为 legacy；RQ/`ingest_kind` 一句；示例键组与 `env_contract.feishu_folder_group_keys` 对齐（含 `NAME`）。

- [ ] **Step 3: 姊妹 plan**  
  确认 [2026-04-26-cloudflare-temp-tunnel-webhook.md](./2026-04-26-cloudflare-temp-tunnel-webhook.md) 顶部 **修订说明** 已合并（本仓库 PR 同批或紧随）：联调配置与 §7 `.env` 真源一致，**不**要求读者仅配 JSON。

- [ ] **Step 4: Commit**  
  `git commit -m "docs(webhook): env-first routing and ingest_kind ops notes"`

---

### Task 8: `dify_upload` — `resolve_dify_target`（§8.2）

**Files:**
- Create: `dify_upload/src/dify_upload/resolve_target.py`
- Modify: `dify_upload/src/dify_upload/__init__.py`
- Create: `dify_upload/tests/test_resolve_target.py`

**签名（可实现微调，语义不变）：**

```python
# dify_upload/src/dify_upload/resolve_target.py
from __future__ import annotations
from pathlib import Path
from typing import Mapping, Any
from .config import DifyTargetConfig


def resolve_dify_target(
    task_context: Mapping[str, Any],
    *,
    env_path: Path,
) -> DifyTargetConfig:
    """Read dify_target_key + dataset_id from task_context; load DIFY_TARGET_<KEY>_* from env_path."""
    ...
```

实现：用 `python-dotenv` 或标准库读 `.env`（与项目一致）；`KEY = task_context["dify_target_key"].strip().upper()`；组后缀与 `onboard` / 根 env 合同一致（`API_BASE`、`API_KEY`、`HTTP_VERIFY`、`TIMEOUT_SECONDS`）。`dataset_id` 来自 `task_context["dataset_id"]`。

- [ ] **Step 1: 单测**  
  `tmp_path` 建 `.env` + 最小 `task_context` → 断言 `DifyTargetConfig` 字段。

- [ ] **Step 2: 实现 + `__init__.py` export**

- [ ] **Step 3: `cd dify_upload; pytest -q`**

- [ ] **Step 4: Commit**  
  `git commit -m "feat(dify_upload): resolve_dify_target from task_context and workspace .env"`

---

### Task 9: `prompts/AGENTS.txt`（§10  checklist）

**Files:**
- Modify: `prompts/AGENTS.txt`

- [ ] **Step 1: 按 spec §10 表 5 行逐条落地**  
  行 3 中写出 **真实** `resolve_dify_target` import 路径（与 Task 8 一致）；禁止遗留占位跨 PR。

- [ ] **Step 2: 根 `AGENTS.md`**  
  若引执行侧模板，仅链到 `prompts/AGENTS.txt`（短句）；遵守 [plan-landed-renew-agents-rules.mdc](../../.cursor/rules/plan-landed-renew-agents-rules.mdc)。

- [ ] **Step 3: Commit**  
  `git commit -m "docs(prompts): AGENTS.txt task_context and Dify resolve contract"`

---

### Task 10: Bootstrap — `doctor`、README、样例 JSON、`sample_qa.md`

**Files:**
- Modify: `bootstrap/src/bootstrap/doctor.py`
- Modify: `bootstrap/README.md`
- Modify: `bootstrap/src/bootstrap/env_dotenv.py`（仅当 `read_env_keys` 行为需扩展以支持 doctor 新键；否则 Step 1 验证只读即可）
- Modify: `bootstrap/src/bootstrap/routing_json.py`（仅当 legacy WARNING 条件需与 `_warn_json_drift` 分支对齐）
- Modify: `bootstrap/src/bootstrap/interactive_setup.py`（stdout：路由真源 `.env` / §7，不误导为仅 JSON 双写）
- Create: `prompts/rules/sample_qa.md`（演示口径：不冒充生产）
- Create: `docs/superpowers/samples/task_context.bootstrap.example.json`
- Modify: `docs/superpowers/samples/pipeline-workspace-root.env.example`（注释块：`FEISHU_FOLDER_ROUTE_KEYS`、示例 `FEISHU_FOLDER_MAIN_*` 五键含 `NAME`、`DIFY_TARGET_DEFAULT_*` 指针）
- Modify: `bootstrap/src/bootstrap/materialize.py`（若需把 `sample_qa` 拷入工作区；与现有 rules 分发逻辑一致）
- Test: `bootstrap/tests/test_doctor.py`
- Test: `bootstrap/tests/test_env_dotenv.py`（`FEISHU_FOLDER_ROUTE_KEYS` 非空时键可读性或 doctor 集成场景，择一最小增量）

- [ ] **Step 1: `doctor`**  
  若 `FEISHU_FOLDER_ROUTE_KEYS` 非空：校验每个 route key 对应 **`feishu_folder_group_keys`**（与 `onboard/env_contract.py` **同源或共享常量**）所列键在 `read_env_keys(workspace/.env)` 中非空。  
  若未配置 ROUTE_KEYS：保留现有 `FOLDER_ROUTES_FILE` 可读性 WARNING；`_warn_json_drift` **仅**在 legacy（未启用 `.env` 路由）时打印或弱化，避免「仅 `.env`、无 JSON」仍刷 BUG-005 噪音。

- [ ] **Step 2: README**  
  BUG-005「JSON 与 `--workspace` 双写」改为 §7 收口后口径（`.env` 真源 + `VLA_WORKSPACE_ROOT`）。

- [ ] **Step 3: 样例 JSON + 样本 env**  
  `task_context.bootstrap.example.json` 含：`ingest_kind`、`dify_target_key`（如 `DEFAULT`）、`dataset_id` 占位、`dataset_id_is_placeholder: true`、`trigger_source: "bootstrap_sample"` 等 §3 演示必填字段。  
  `pipeline-workspace-root.env.example` 按上文文件表增补（与 **跨 plan 第 3 条**一致）。

- [ ] **Step 4: `cd bootstrap; pytest`**

- [ ] **Step 5: Commit**  
  `git commit -m "feat(bootstrap): doctor env routes and sample task_context"`

---

### Task 11: `feishu_fetch`、生产 bootstrap design、本 spec 状态

**`ThirdParty.md`、`ENV-OLD-TO-NEW.md` 在本 plan 中仅此 Task 改；与文首跨 plan §4 对齐。**

**Files:**
- Modify: `feishu_fetch/README.md`
- Modify: [2026-04-28-production-bootstrap-deployment-design.md](../specs/2026-04-28-production-bootstrap-deployment-design.md)（§3.2 修订说明，与 docedit）
- Modify: [2026-04-28-task-context-bootstrap-sample-agent-contract-design.md](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) 文首落地状态（**与 plan 同 PR 末次 commit**；成对更新）
- Modify: `ThirdParty.md`（登记 webhook 依赖 `python-dotenv`；表格格式遵从仓库既有 **ThirdParty** 惯例）
- Modify: `ENV-OLD-TO-NEW.md`（**顶部 `## 修订说明`**：webhook 文件夹路由以 task-context spec §7 **`.env` 真源** 为准，`FOLDER_ROUTES_FILE` 仅 legacy 回退；与正文 §1 表格「业务映射」句互补）

- [ ] **Step 1: README**  
  标明生产 `ingest_kind` 真源为 `task_context.json`；`FeishuFetchRequest.ingest_kind` 必须一致。

- [ ] **Step 2: production bootstrap design**  
  BUG-005 关单叙述：`pipeline_workspace.path` 与 `VLA_WORKSPACE_ROOT` / `.env` 父目录、`CURSOR_RUN_TIMEOUT_SECONDS` 对齐。

- [ ] **Step 3: 验收跑通**  
  - `cd webhook; pytest`  
  - `cd dify_upload; pytest`  
  - `cd bootstrap; pytest`  
  - 触及 `feishu_fetch` 测试则同跑

- [ ] **Step 4: Commit**  
  `git commit -m "docs: align feishu_fetch and bootstrap design with task_context contract"`

---

## Self-Review（plan 作者自检）

**1. Spec coverage**

| Spec 区块 | Task |
|-----------|------|
| §2.3 占位 / AGENTS 兜底 | Task 6、9 |
| §3 字段表 | Task 1、5、6、10 |
| §7.1–§7.3 webhook | Task 2–7 |
| §7.5 bootstrap 样例 | Task 10 |
| §7.6 Redis | Task 4 |
| §8 薄封装 | Task 8、9 |
| §9 bootstrap 联动 | Task 10、11 |
| §10 AGENTS | Task 9 |
| 文首单次交付 | 全 Task 同一合并批次 |
| 跨 plan / `settings.py` / 样本 env / 隧道脚本 | 文首 **跨 plan 合并与联动**；Task 7、10 |
| `ThirdParty` / `ENV-OLD-TO-NEW` | **仅 Task 11**（文首 §4 指针） |

**2. Placeholder scan**  
无 TBD；Redis 策略在 Task 4 显式对齐 spec §7.6（b）类；`derive_ingest_kind` 映射在 Task 5 写死或指向姊妹 design 真值表。

**3. Type consistency**  
`TaskContext` / `DocumentSnapshot` / `FolderRoute` / RQ kwargs 均使用 `ingest_kind: str`、`dify_target_key: str`；与 `resolve_dify_target(task_context, env_path)` 键名一致。

---

## Execution Handoff

Plan：`docs/superpowers/plans/2026-04-28-task-context-bootstrap-sample-agent-contract-implementation-plan.md`。

**默认执行方式：** **Subagent-Driven** — 每 Task 子代理，`superpowers:subagent-driven-development`。同一会话连续跑完全部 Task 时可用 **Inline Execution** + `superpowers:executing-plans` 检查点。**无必选交互**。
