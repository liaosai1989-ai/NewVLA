# Feishu Fetch + Lark CLI Workspace Init Implementation Plan

> **落地状态：已落地**（2026-04-27；实现与下文 Task 1–6 及自检表一致，代码见仓库 `feishu_fetch/`、`onboard/操作手册.md` cwd 段、`BugList.md` BUG-001 包内核对。）

> **修订（2026-04-27 后续）：** 下文若仍出现「`settings.lark_cli_command` / 从 `.env` 读 `LARK_CLI_COMMAND`」字句，以**本段为准**覆盖：根 `.env` **禁止**再写 `LARK_CLI_COMMAND`（`load_feishu_fetch_settings` 见键即 **`ValueError`**）；`FeishuFetchSettings` **不含** `lark_cli_command`；`facade` 子进程固定经 `PATH` 解析命令名 **`lark-cli`**（实现为模块内 `_LARK_CLI`，非用户可配项）。详见仓库 `feishu_fetch/src/feishu_fetch/config.py`、`facade.py`。

> **修订（2026-04-27，`cloud_docx` argv）：** 下文或自检表若仍写 `docs +fetch` 的 **`--document-id`** / **`--scope docx`**，以**本段为准**覆盖：现行 `lark-cli` 使用 **`--doc`**（文档 URL 或 token）；**不使用** `--document-id`；**不使用** `--scope docx`（整篇读取依 v2 默认 `scope`）。实现见 `feishu_fetch/src/feishu_fetch/facade.py` 及同目录测试/fixture。**正文任务步骤不改写。**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]` / `- [x]`) syntax for tracking.

**Goal:** 落地 [2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](../specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md)：凭证归 `onboard` / 初始化层；`feishu_fetch` 只读根 `.env` 中 **`FEISHU_REQUEST_TIMEOUT_SECONDS`、`FEISHU_APP_ID`**（仅与 `config show` 做 appId 比对）；**不**读、**不**兼容 `LARK_CLI_COMMAND`；子进程命令名固定 **`lark-cli`**；预检 `config show`，错误按 §10 分类；测试分 L0（默认 CI）与 L1（显式门控真云）。

**Architecture:** 在 `feishu_fetch` 包内新增 `config` 与预检逻辑：从根 `.env` 加载 **非 exec 类**设置；抓取前顺序执行「可执行性（`shutil.which("lark-cli")`）→ `config show` 解析与 `FEISHU_APP_ID` 一致性」；**所有** lark 子进程 argv[0] 均为解析后的 `lark-cli` 可执行路径（来源 `facade`，**非** `FeishuFetchSettings` 字段）。`onboard` 已含 `lark_config_init` / `lark_config_show_verify_app_id`，本计划只要求与 `feishu_fetch` 侧 `config show` 调用与 JSON 解析规则一致，并在文档中固定「工作区根 + 相同 cwd」约定。不扩张抓取矩阵、不引入交互式登录。

**Tech Stack:** Python 3.10+，`subprocess`，`pytest`，可选 `pytest` marker 做 L1 门控（不新增 `httpx` 等非本 spec 依赖）。

### 执行上下文不变量（spec §6.1，实现必守）

- **根 `.env` 真源：** `env_file` 必须指**管线工作区根**下的 `.env`。解析方式二选一且须写进 `load_feishu_fetch_settings` 与 README：（1）调用方显式传入 `env_file=Path`；（2）环境变量 `FEISHU_FETCH_ENV_FILE` 指向该 `.env` 的**绝对路径**；若皆无，则 `env_file = Path.cwd() / ".env"` 且 **约定此时进程 cwd 即为工作区根**（与 `onboard` 执行 `lark_config_init(cwd=...)` 的目录一致）。
- **工作区根字段：** `FeishuFetchSettings.workspace_root = env_file.resolve().parent`，供全链路复用。
- **全部 lark 子进程**（`--help`、`config show`、及 `docs`/`drive` 等正文抓取）在 `subprocess.run` 中传 **`cwd=settings.workspace_root`**，与 `onboard` 中 `lark_config_init` / `lark_config_show_verify_app_id` 使用的 `cwd` 为同一物理目录。禁止仅预检设 `cwd`、抓取不设。

### 第三方依赖与可执行文件（对齐 `BugList.md` **BUG-001**）

本计划涉及的外部依赖分两类，**落代码前、合并前**各审一遍，禁止只修 MarkItDown、漏掉 lark 或其它路径。

**A. 外部可执行文件（经 `subprocess` 等拉起）**

- 本 spec 范围内 **仅** `lark-cli` CLI：入口为 **固定命令名** `lark-cli` + `shutil.which`（与 `onboard` 一致），**禁止**在根 `.env` 配置可执行名或路径；若 `.env` 仍含已废弃键 `LARK_CLI_COMMAND`，**加载设置阶段即失败**（须删键）。排障用「把 CLI 安装目录加入 PATH」。
- 本计划**不**新增对其它可执行文件（`node`、`curl`、`markitdown` CLI 等）的调用；若今后扩展，须先过 BUG-001 同口径，不得默认可执行路径进 `.env`。

**B. Python 第三方库（如 MarkItDown）**

- 在 **`feishu_fetch/pyproject.toml`** 声明可安装依赖；运行时用 **`importlib.import_module` / 正常 `import`**，由当前 Python 环境解析。
- **禁止**：为这类库再引入「`MARKITDOWN_COMMAND` / 可执行文件绝对路径」等旁路；缺包时错误信息指向 **安装依赖 / 使用正确 venv**，而非教用户硬编码本机工具路径。

**C. 合并前自检（本计划改动的 `feishu_fetch/` 必做）**

- 全文检索：`subprocess` / `Popen` / `os.system` / `shell=True` / 硬编码 `\.exe` 或 `C:\\` 等可疑路径、除 **`lark-cli` 实现路径**外的 `*_COMMAND` 环境键（根 `.env` 不应再出现 `LARK_CLI_COMMAND`）。
- 对照上表 A/B：凡不符合 BUG-001 的，**修掉或写进例外**（须文档可审查；默认不接受未文档化旁路）。

**D. 关单与总表**

- 本包按上项验收后，可在 `BugList.md` **BUG-001** 中把 `feishu_fetch` 标为已扫；**全仓**其它模块仍走原 bug 的「全仓审计」关单条件。

### `build_error` 的 `code` 与 §10 映射（实现按表固定，避免混用）

| 场景 | `code` | `reason`/用户可见补充 |
|------|--------|-------------------------|
| §10.1 找不到可执行、进程无法启动 | `dependency_error` | `reason`/`advice` 指向 **PATH 上缺少 `lark-cli`**（命令名固定，不经 settings） |
| §10.2 未初始化、`config show --json` 失败/不可解析/无 appId、与根 `.env` 的 `FEISHU_APP_ID` 不一致 | **`lark_config_error`（唯一，不用 `dependency_error` 混用）** | 与 §10.2 建议口径一致，区分于 §10.1 |
| §10.3 应用/bot 对目标无权限 | **`permission_error`（唯一，不回落到 `runtime_error`）** | 启发式命中 stderr 关键词时（Task 4） |
| 其他 lark 业务失败 | 沿用现有 `runtime_error` 等 | `reason`/`advice` 中命令名与 `detail["command"]` 与实现一致（`lark-cli` + 子参数） |

---

## 文件结构（本 spec 范围内）

| 路径 | 职责 |
|------|------|
| `feishu_fetch/src/feishu_fetch/config.py` | `FeishuFetchSettings`（含 `workspace_root`、`request_timeout_seconds`、预检用只读 `feishu_app_id`；**无** `lark_cli_command`）、`load_feishu_fetch_settings`（若 `.env` 含 `LARK_CLI_COMMAND` 则 `ValueError`） |
| `feishu_fetch/src/feishu_fetch/lark_env.py` | 解析 `lark-cli config show` stdout 的 `appId`（与 onboard 已用 `--json` 行为对齐）；可单测锁样例 |
| `feishu_fetch/src/feishu_fetch/facade.py` | 注入 settings；子进程入口 **固定** `lark-cli`（模块内 `_LARK_CLI` + `shutil.which`）；**全部** lark 子进程 `cwd=settings.workspace_root`；预检串联；权限不足启发式（§10.3） |
| `feishu_fetch/src/feishu_fetch/errors.py` | **须**增加 `lark_config_error`、`permission_error`（及现有 `dependency_error`/`runtime_error`），与文首表一一对应，禁止再写「或」分支 |
| `feishu_fetch/src/feishu_fetch/__init__.py` | 导出 `FeishuFetchSettings`、`load_feishu_fetch_settings`（若对外需要） |
| `feishu_fetch/README.md` | 合同：初始化层 vs 模块；声明支持的 `lark-cli` 版本/子命令；环境变量表 |
| `feishu_fetch/tests/test_config.py` | 加载、校验、`FEISHU_REQUEST_TIMEOUT_SECONDS` 正数 |
| `feishu_fetch/tests/test_lark_env.py` | `config show` 样例 JSON 解析、失败分支 |
| `feishu_fetch/tests/test_facade.py` | 预检失败；`subprocess` 断言带 `cwd=workspace_root`；`which`/`argv` 与 `lark-cli` 一致 |
| `feishu_fetch/tests/test_models.py` | 错误示例文案与 `dependency_error` 展示命令数组一致 |
| `onboard/README.md` 或 `onboard/操作手册.md` | 补一段：init 与 Agent 任务须同一工作区根、同 cwd 约定（§6.1） |
| `.env.example` | **勿**列 `LARK_CLI_COMMAND`；含 `FEISHU_REQUEST_TIMEOUT_SECONDS` 等；确认不重新引入 `MARKITDOWN_COMMAND` |
| `docs/.../spec` | 已按 docedit 将本 plan 与同名 spec 标为已落地（本行随落地回写更新） |

---

### Task 1: `config.py` 与 `FeishuFetchSettings`

**Files:**

- Create: `feishu_fetch/src/feishu_fetch/config.py`
- Modify: `feishu_fetch/src/feishu_fetch/__init__.py`
- Test: `feishu_fetch/tests/test_config.py`

- [x] **Step 1: 写失败测试（settings 与校验）**

在 `feishu_fetch/tests/test_config.py`：

```python
from __future__ import annotations

from pathlib import Path

import pytest

from feishu_fetch.config import FeishuFetchSettings, load_feishu_fetch_settings


def test_load_minimal_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "FEISHU_REQUEST_TIMEOUT_SECONDS=90",
                "FEISHU_APP_ID=cli_abc",
            ]
        ),
        encoding="utf-8",
    )
    s = load_feishu_fetch_settings(env_file=env_file)
    assert s.request_timeout_seconds == 90.0
    assert s.feishu_app_id == "cli_abc"
    assert s.workspace_root == env_file.resolve().parent


def test_rejects_deprecated_lark_cli_command_in_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LARK_CLI_COMMAND=lark-cli\nFEISHU_REQUEST_TIMEOUT_SECONDS=60\nFEISHU_APP_ID=cli_x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="LARK_CLI_COMMAND"):
        load_feishu_fetch_settings(env_file=env_file)


def test_timeout_must_be_positive(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FEISHU_REQUEST_TIMEOUT_SECONDS=0\nFEISHU_APP_ID=x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="FEISHU_REQUEST_TIMEOUT"):
        load_feishu_fetch_settings(env_file=env_file)
```

- [x] **Step 2: 运行测试确认失败**

```powershell
Set-Location "c:\Cursor WorkSpace\NewVLA\feishu_fetch"
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v
```

预期：导入失败 / `load_feishu_fetch_settings` 未定义。

- [x] **Step 3: 最小实现**

新建 `feishu_fetch/src/feishu_fetch/config.py`：

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_dotenv_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    raw = path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k:
            out[k] = v
    return out


def _resolve_env_file(
    env_file: Path | None, environ: dict[str, str]
) -> Path:
    if env_file is not None:
        return env_file.resolve()
    raw = (environ.get("FEISHU_FETCH_ENV_FILE") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.cwd() / ".env").resolve()


@dataclass(frozen=True)
class FeishuFetchSettings:
    request_timeout_seconds: float
    feishu_app_id: str
    env_file: Path
    workspace_root: Path


def load_feishu_fetch_settings(
    *,
    env_file: Path | None = None,
    environ: dict[str, str] | None = None,
) -> FeishuFetchSettings:
    env = environ if environ is not None else os.environ
    env_file = _resolve_env_file(env_file, env)
    workspace_root = env_file.parent
    values = _parse_dotenv_file(env_file)
    if "LARK_CLI_COMMAND" in values:
        raise ValueError(
            "根 .env 含已废弃键 LARK_CLI_COMMAND，请整行删除；"
            "feishu_fetch 子进程只使用命令名 lark-cli（由 facade 直接调用，不经 .env 配置）"
        )
    raw_timeout = (values.get("FEISHU_REQUEST_TIMEOUT_SECONDS") or "60").strip()
    feishu_app_id = (values.get("FEISHU_APP_ID") or "").strip()
    if not feishu_app_id:
        raise ValueError("根 .env 缺少 FEISHU_APP_ID，无法与 lark-cli config show 的 appId 做一致性比对")
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise ValueError("FEISHU_REQUEST_TIMEOUT_SECONDS 不是合法数字") from exc
    if timeout <= 0 or timeout != timeout:  # nan
        raise ValueError("FEISHU_REQUEST_TIMEOUT_SECONDS 必须是正数")
    return FeishuFetchSettings(
        request_timeout_seconds=timeout,
        feishu_app_id=feishu_app_id,
        env_file=env_file,
        workspace_root=workspace_root,
    )
```

在 `__init__.py` 中：

```python
from .config import FeishuFetchSettings, load_feishu_fetch_settings

__all__ = [
    "FeishuFetchError",
    "FeishuFetchRequest",
    "FeishuFetchResult",
    "FeishuFetchSettings",
    "fetch_feishu_content",
    "load_feishu_fetch_settings",
]
```

- [x] **Step 4: 运行测试通过**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v
```

预期：全部 PASS。

- [x] **Step 5: Commit**

```bash
git add feishu_fetch/src/feishu_fetch/config.py feishu_fetch/src/feishu_fetch/__init__.py feishu_fetch/tests/test_config.py
git commit -m "feat(feishu_fetch): add settings loader for lark workspace contract"
```

---

### Task 2: `lark_env.py` — 解析 `config show`

**Files:**

- Create: `feishu_fetch/src/feishu_fetch/lark_env.py`
- Test: `feishu_fetch/tests/test_lark_env.py`

- [x] **Step 1: 失败测试**

`feishu_fetch/tests/test_lark_env.py`：

```python
import json

import pytest

from feishu_fetch.lark_env import parse_config_show_json, app_id_from_config_show_payload


def test_parse_minimal_config_show() -> None:
    payload = {"appId": "cli_xxx", "brand": "Feishu"}
    stdout = json.dumps(payload, ensure_ascii=False)
    data = parse_config_show_json(stdout)
    assert app_id_from_config_show_payload(data) == "cli_xxx"


def test_app_id_alias() -> None:
    payload = {"app_id": "cli_yyy"}
    assert app_id_from_config_show_payload(payload) == "cli_yyy"


def test_empty_app_id_fails() -> None:
    with pytest.raises(ValueError):
        app_id_from_config_show_payload({})
```

- [x] **Step 2: 运行失败**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_lark_env.py -v
```

- [x] **Step 3: 实现**

`feishu_fetch/src/feishu_fetch/lark_env.py`：

```python
from __future__ import annotations

import json
from typing import Any


def parse_config_show_json(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        raise ValueError("config show 无输出")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("config show 顶层不是 JSON 对象")
    return data


def app_id_from_config_show_payload(data: dict[str, Any]) -> str:
    aid = data.get("appId") or data.get("app_id")
    s = str(aid).strip() if aid is not None else ""
    if not s:
        raise ValueError("config show 中缺少非空 appId")
    return s
```

- [x] **Step 4: pytest 通过；Step 5: commit**（消息：`feat(feishu_fetch): parse lark-cli config show JSON for appId preflight`）

**注：** spec §9.2 正文写 `lark-cli config show`；与 `onboard` 及本计划一致，**实际 argv 为** `config show --json`（stdout 单段 JSON，便于测与解析）。

---

### Task 3: `facade` — 预检 `config show` + 固定 `lark-cli` 入口

**Files:**

- Modify: `feishu_fetch/src/feishu_fetch/facade.py`
- Modify: `feishu_fetch/tests/test_facade.py`
- Modify: `feishu_fetch/tests/fixtures/mock_lark_cli.py`（若需）
- Modify: `feishu_fetch/tests/test_models.py`（`detail["command"]` 与 `dependency_error` 文案以 `lark-cli` 为准）
- Modify: `feishu_fetch/src/feishu_fetch/errors.py`（**须**落地 `lark_config_error`、`permission_error`）

**行为要点（来自 spec §9.2、§9.3；修订后）：**

1. `fetch_feishu_content` 开头：`load_feishu_fetch_settings()`；`timeout` 默认用 `settings.request_timeout_seconds` 与 `request.timeout_seconds` 的合并规则（建议：`request.timeout_seconds` 若置位则覆盖默认）。
2. 抽象 `_run_lark_cli`（或同等）：凡调 lark，命令名固定 **`lark-cli`**（模块内 `_LARK_CLI`），经 `shutil.which` 得绝对路径；必传 `cwd=settings.workspace_root`（与上节不变量一致）。
3. `_ensure_lark_cli_available`：运行 `[resolved, "--help"]`（`resolved` 来自 `which("lark-cli")`）。
4. `_ensure_lark_config_matches_env(...)`：**预检 argv 固定** `[resolved, "config", "show", "--json"]`，`cwd=settings.workspace_root`；解析 JSON；`appId` 与 `settings.feishu_app_id` 比较。失败时 **`code="lark_config_error"`** 唯一；与 §10.1 的 `dependency_error` 区分；文案中展示名用 **`lark-cli`**（与子进程一致）。
5. `_fetch_cloud_docx` / `drive` 等：子参数拼在 `resolved` 之后；**每条** `subprocess.run` 均带 `cwd=settings.workspace_root`。

**禁止：** `subprocess` 给子进程 `env` 塞 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`。

- [x] **Step 1: 更新 `test_facade` 里 monkeypatch `shutil.which`**

让 fake 对 `lark-cli`（及 `.cmd`/`.exe` 等）可解析，并 mock `subprocess.run` 序列：`--help` 成功 → `config show --json` 成功且 stdout 为带 `appId` 的 JSON（与 `settings` 中 `FEISHU_APP_ID` 一致）；**断言每次调用 `kwargs["cwd"]` 等于 `workspace_root`**（由临时 `.env` 推出）。**勿**再在测试 `.env` 中写 `LARK_CLI_COMMAND`（加载会失败）。

- [x] **Step 2: 实现 facade 改动后跑 `pytest tests/test_facade.py -v`**

- [x] **Step 3: 全量 `feishu_fetch` pytest**

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

- [x] **Step 4: Commit** — `feat(feishu_fetch): preflight config show and unify lark CLI command path`

---

### Task 4: §10.3 应用权限不足 — 启发式

**Files:**

- Modify: `feishu_fetch/src/feishu_fetch/facade.py`
- Test: `feishu_fetch/tests/test_facade.py`（对 `_require_success` 或 cloud_docx 失败分支打桩 stderr）

- [x] **Step 1: 在 `lark-cli` 已预检通过前提下，对 `returncode != 0` 的 stderr 做关键词/短语允许列表**（中或英可配置小集合，可维护，避免整段全匹配）。命中则 **`code="permission_error"`**（文首表唯一，与 `runtime_error` 不混用）；`reason` 对齐 spec「应用权限不足」类文案。

- [x] **Step 2: 测试：模拟 stderr 含典型无权限提示 → 错误归类为 `permission_error`；无匹配时仍走通用 `runtime_error`（`reason`/`detail` 与 `lark-cli` 子命令展示一致）。

- [x] **Step 3: Commit** — `fix(feishu_fetch): classify lark permission errors for cloud_docx path`

---

### Task 5: 文档与 onboard 约定

**Files:**

- Modify: `feishu_fetch/README.md`
- Modify: `onboard/操作手册.md` 或 `onboard/README.md`（二选一，与现有风格一致）

- [x] **Step 1: `feishu_fetch/README.md` 增加章节**：环境变量（`FEISHU_REQUEST_TIMEOUT_SECONDS`、`FEISHU_APP_ID`）；**禁止** `LARK_CLI_COMMAND`（见键即加载失败）；`FEISHU_FETCH_ENV_FILE` 可选；**进程 cwd=工作区根**或显式绝对路径；说明 `FEISHU_APP_SECRET` 不由本模块读取；先由 `onboard`（或手工）完成 `lark-cli config init`；列 supported `lark-cli` 子命令版本说明占位（指向仓库某固定次版本实测）。**并写清**：子进程固定 `lark-cli`+PATH；Python 类依赖（如 MarkItDown）= `pyproject` + venv，见文首 **BUG-001** 节。

- [x] **Step 1b: BUG-001 合并前自检** — 在 `feishu_fetch/` 执行文首 **§第三方依赖** 小节 C 的检索与对照；有改动则进同一 PR 或跟票。

- [x] **Step 2: onboard 文档补 3–5 行**：`lark_config_init` 的 `cwd` 必须等于执行工作区根，与 `feishu_fetch` 抓取时进程 `cwd` 一致（§6.1）。

- [x] **Step 3: Commit** — `docs: align feishu_fetch and onboard lark workspace context`

---

### Task 6: L0 / L1 测试分层

**Files:**

- Modify: `feishu_fetch/pyproject.toml`（如尚无 markers）
- Create 或修改: `feishu_fetch/tests/conftest.py`（注册 `integration` / `l1_cloud` marker）
- Create: `feishu_fetch/tests/test_cloud_docx_integration_l1.py`（默认 `skip`）

- [x] **Step 1: 在 `pyproject.toml` 的 `[tool.pytest.ini_options]` 增加 `markers`：`l1_cloud: 真云 lark 集成，需显式环境变量`**

- [x] **Step 2: L1 文件模板**（实现体留空或 `pytest.skip` 直到有 secrets）：

```python
import os
import pytest

pytestmark = pytest.mark.l1_cloud


@pytest.mark.l1_cloud
def test_cloud_docx_authorized_real() -> None:
    if not os.environ.get("FEISHU_FETCH_L1_RUN"):
        pytest.skip("set FEISHU_FETCH_L1_RUN=1 and configure doc tokens")
    # 在实现真断言之前保留下一行，避免受控机只开 RUN 即因 assert False 红：落地后删 skip 并写真实 document_id
    pytest.skip("L1 授权路径尚未接真云，删除本行后补全")
    # 使用真实 document_id，断言 fetch 成功


@pytest.mark.l1_cloud
def test_cloud_docx_unauthorized_real() -> None:
    if not os.environ.get("FEISHU_FETCH_L1_RUN"):
        pytest.skip("set FEISHU_FETCH_L1_RUN=1 and configure doc tokens")
    pytest.skip("L1 未授权路径尚未接真云，删除本行后补全")
    # 未授权文档，断言 permission 类错误
```

- [x] **Step 3: 在 `feishu_fetch/README.md` 说明 L1 如何开启；CI 默认不跑 L1。**

- [x] **Step 4: Commit** — `test(feishu_fetch): add gated L1 cloud_docx integration placeholder`

---

## 自检（本计划 vs spec）

| Spec 条款 | 覆盖 Task |
|-----------|-----------|
| §7.2 模块只保留 TIMEOUT、appId 只读（**无** exec 名配置） | Task 1 |
| §9.1 统一命令入口（固定 `lark-cli` + `which`，不经 settings） | Task 3 |
| §9.2 预检顺序与 appId 比对 | Task 2, 3 |
| §9.3 禁止 env 注入凭证 | Task 3 显式禁止 |
| §10.1–10.2 错误口径与可区分 `code` | 文首映射表 + Task 3 + `errors.py` |
| §10.3 权限不足 | Task 4 |
| §11.2 测试方向 | Task 1–4, 6 |
| §11.3 L0/L1 | Task 6 |
| §6.1 执行上下文（`cwd` + 根 `.env`） | Task 1、3、5（不变量文首+实现） |
| `BugList.md` BUG-001 全类第三方（lark+Python 库+合并前 grep） | 文首 A–D 节、Task 5 Step 1/1b |
| 不重写抓取矩阵 / 不 OAuth | 各 Task 不触及矩阵扩展 |

**占位符扫描：** 本计划无 TBD；L1 用**第二层 `pytest.skip`** 占位，受控机开 `FEISHU_FETCH_L1_RUN=1` 时默认仍 skip，避免误红；**合并进主分支前**须换成真断言或明确文档说明仅手工跑。

**§11.3 L2：** 发布前 Go/No-Go 真云步归属运维/流水线清单，本实现计划不展开命名；与默认 PR 解耦，与 spec 一致。

---

**执行：** 子代理按 task 用 `subagent-driven-development`，或同会话用 `executing-plans` 与检查点。本文档路径：`docs/superpowers/plans/2026-04-27-feishu-fetch-lark-cli-workspace-init-implementation-plan.md`。
