# Production Bootstrap 部署实现计划

> **废止与接替（2026-04-28，NTH-008 / Task 10）：** 本文 **Architecture** 中 **`tools/*` Windows junction**、正文 **Task 6 `junction.py`**、CLI **`--no-junction-tools`**、验收矩阵「**实机 + junction**」等叙述 **已废止**。**现行实现与验收合同**以 [**2026-04-28-workspace-embedded-runtime-implementation-plan.md**](./2026-04-28-workspace-embedded-runtime-implementation-plan.md) 为准：**实拷贝** **`vla_env_contract/`**、**`runtime/webhook/`**、**`tools/*`**；**`bootstrap install-workspace-editables`**；**`bootstrap probe`**；**`GET /health`**。下文历史任务块（含 junction 代码片段）**仅供对照**，**不得**当作当前合并闸门或签字前提。

## 修订说明

- **2026-04-28（Task 10）：** 文顶 **废止通告** 与 [**production-bootstrap-deployment-design.md** §3.4](../specs/2026-04-28-production-bootstrap-deployment-design.md) **实拷贝**对齐；**junction** 相关 Task **由 workspace-embedded implementation plan 取代**。

- **2026-04-28（联动 task-context 合同 plan）：** `webhook/src/webhook_cursor_executor/settings.py` 须与 [2026-04-28-task-context-bootstrap-sample-agent-contract-implementation-plan.md](./2026-04-28-task-context-bootstrap-sample-agent-contract-implementation-plan.md) **同一合并窗口、prefer 单作者串行**：先落地本 plan **Task 12**（`_env_file()`、`DotEnvSettingsSource`、`test_env_file_uses_vla_workspace_root`），再在同一 PR/commit 链叠加 task-context **Task 2**（`load_routing_config`、`.env`/JSON 分支、`FolderRoute.dify_target_key`）。**禁止**并行 PR 各改一半 `settings.py`。
- **2026-04-28：** 文件夹路由真源以 task-context spec §7 为准（`FEISHU_FOLDER_ROUTE_KEYS` + `feishu_folder_group_keys` 各组键，**推荐含 `NAME`**，与 `onboard/env_contract` 一致）。BUG-005 收口后，本文内「仅 JSON / 双写」类表述以 task-context 批次修订为准；不在本 plan 重复实现 §7 路由逻辑。
- **2026-04-28（BUG-007）：** Windows 下克隆路径某段含空格时，若 **`pip install -e`** 的 editable 目标被解析为**子包绝对路径**，同源 **`file:../vla_env_contract`** 等可能被 pip 错位展开。**缓解：** `install_packages.install_all` 对每个子包 **`cwd=<pkg>` + `pip install -e .`**；**工作区** **`bootstrap install-workspace-editables`**；**`run-unattended-acceptance.ps1`** 在 **`bootstrap` 目录内**执行 **`pip install -e ".[test]"`**（`Push-Location`/`Pop-Location`）。复现与验证命令见 **`BugList.md` BUG-007**；**`bootstrap/README.md`** 含人手首装备注。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在仓库根新增可安装的 `bootstrap/` 包，提供 `doctor`、`install-packages`、`materialize-workspace` 子命令与 `bootstrap/README.md` 生产首启清单，满足 `docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md` 的 P0 验收。**用户验收唯一路径：** clone/拷贝维护仓后，PowerShell **一条顺序命令**装包并进入 **`bootstrap interactive-setup`**，在终端 **连续键入** 所需参数，由程序编排 `install` → `materialize` → 提示编辑工作区 `.env` → `doctor`（见「理想交互流程」与 **Task 13**，**P0 必交付**）。`doctor` / `install-packages` / `materialize-workspace` **分立子命令**保留给 **CI、自动化脚本与排障**，**不得**当作与人验收对等的并列入口；Task 13 仅编排调用既有 API，**不**复制物化/自检逻辑。**Task 14（落地闸门）：** Task 1–13 实现完成后 **必须**跑通 **`run-unattended-acceptance.ps1`**：**merge/CI** 以 **`-SkipDoctor`**（**A 档**：install→materialize→样本覆盖 `.env`）**exit 0** 为准；维护机另跑 **B 档**（含 **`doctor`**）。**不**替代人机签字。

**与 task-context / feishu_fetch 合同同期交付（本期须勾选）：** 按 `docs/superpowers/specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md` 文首 **「本期实现范围」** 与 **「单次交付，禁止拆分」**，**须**在同一合并批次 / 验收窗口内完成：以 **`webhook_cursor_executor` 为主**的 **`ingest_kind`** 写入 **`DocumentSnapshot`、`TaskContext`、落盘 `task_context.json`**（`app` / `worker` / `scheduler`、RQ 入参、解析规则、单测、§7.6 Redis 策略），以及该 spec §8 / §9 / §10 / `feishu_fetch` README 等所列**同批**条目；**不得**拆分 PR 使 §7–§10 主线悬空，**不因**本 plan 文件名侧重 bootstrap 而将 `ingest_kind` 或路由收口推迟到未命名后续批次。

**Architecture（现行）：** 单机统一 Python（≥3.12，无 venv）、`bootstrap` 依赖标准库 + `redis` + **`vla-env-contract`**（`file:`）。`materialize-workspace` 在 **`--workspace` 目录根** 落 **运行合同 `.env`**、同步 `prompts/` → `AGENTS.md` + `rules/**`，并 **递归拷贝** **`vla_env_contract/`**、**`runtime/webhook/`**、**`tools/dify_upload`**、**`tools/feishu_fetch`**（**不**使用 junction；见 **workspace-embedded** implementation plan）。生产签字含 **`bootstrap install-workspace-editables --workspace`** 与 **`bootstrap probe`**。**不**再把「维护仓库克隆根」当作 **运行侧** 合同 `.env` 的唯一落点。

**真源口径（与 `2026-04-28-production-bootstrap-deployment-design.md` §2.1 一致）：**

1. **两份根 `.env`，职责分开：** **维护仓库根** `{CLONE_ROOT}/.env` = 本仓库/克隆机上的 **维护与初始化种子**（非执行工作区的运行合同真源）。**执行工作区根** `{WORKSPACE_ROOT}/.env` = **运行合同唯一真源**（`cursor agent` cwd 同层；`VLA_WORKSPACE_ROOT` 指向工作区时 webhook 加载此文件）。
2. **初始化时怎么来：** **首次 `materialize-workspace`** 以 **`{CLONE_ROOT}/.env` 整份复制**到工作区根；若无克隆根 `.env`，允许 `.env.example` → 工作区或 `--seed-env`（见 Task 7）。物化完成后，**运行相关键以工作区根 `.env` 为准**。
3. **初始化时谁读谁写：** **`doctor --workspace`**、生产 webhook（`VLA_WORKSPACE_ROOT` 指向工作区时）等读 **`{WORKSPACE}/.env`**。**运行侧生效的合同键须落在工作区根 `.env`**。若 **`feishu-onboard`** 等交互只写入维护仓库根 `.env`（默认行为），**不会**自动镜像到工作区；须按 **`bootstrap/README.md` 交接清单** 手工合并或复制到工作区根 `.env`（与 spec §4.2、Task 10 一致；后续若改 onboard 写入路径另述）。

**路径表达：** 执行工作区根 **仅由 CLI `--workspace`**（及物化时同一参数）表达；**不**在 `.env` 再存 `PIPELINE_WORKSPACE_PATH`。加载 `{WORKSPACE_ROOT}/.env` 时，工作区根 = **该文件父目录**（或进程 cwd 已设为工作区根）。**门禁**对工作区路径只做 `validate_workspace_root_path(--workspace)`，**不**比对 env 内重复键。`FOLDER_ROUTES_FILE` JSON **不作为**门禁；可读且 `pipeline_workspace.path` 与 `Path(--workspace).resolve()`（规范化）不一致 → **WARNING**（BUG-005 / webhook 仍读 JSON）。

**`.cursor/rules/env.mdc`：** 已写入双 `.env` 语境（维护仓 vs 工作区）。**根 `AGENTS.md` / `prompts/AGENTS.txt`：** 落地 bootstrap 后须 **renew** onboard 相关句，明示 **运行真源 = 工作区根 `.env`**、onboard 写维护仓后须 **同步到工作区**（与 spec §4.2 一致）。

**Tech Stack:** Python 3.12+、setuptools、`redis` PyPI、`pytest`（仅测试依赖）；物化为 **`shutil.copytree`** + ignore（**非** junction）

**路径约定（全文一致）：**

- **维护仓库根** = 本仓库 **`git clone` 或拷贝到客户机后的目录**，每台机器、每次部署都不同；plan 内 **禁止** 写死某盘符或某开发者本机路径。
- **执行工作区根** = **`materialize-workspace --workspace`** 传入的绝对路径，由 **客户/现场运维指定**（须满足 design spec §3.2；与 `VLA_WORKSPACE_ROOT` 同字符串）。
- **与「不写死客户盘符」并存：** Task 14 / 闸门脚本中的 **`C:\Cursor WorkSpace\VLA_workplace`** 等为 **本仓库维护机可覆盖的参数示例**，方便对齐 **§3.2** 真源口径；**正文占位仍以** **`<CLONE_ROOT>`、`$WORKSPACE`** **为准**，示例路径 **不得**当作全局默认值写进代码常量。
- 各 Task 的 `Run:`、git、PowerShell 示例：用 **`<CLONE_ROOT>`** 占位，或先设 **`$CLONE_ROOT` / `$WORKSPACE`** 再执行（与文末「用户验收主流程」占位约定同套路）。

### 理想交互流程（**用户验收唯一路径**）

1. 用户 **clone 或拷贝** 本维护仓库到本机任意目录（`{CLONE_ROOT}`）。
2. 打开 **PowerShell**，`Set-Location` 到该目录，执行 **一条启动链**（先 `pip install -e .\bootstrap[…]`，再 **`bootstrap interactive-setup`**，**Task 13，P0 必含**）。
3. 在终端里 **按提示交互输入**：维护仓库根（默认 `Path.cwd()` 且须通过 `assert_clone_root_looks_sane`）、执行工作区根绝对路径、可选用 **`--dry-run` 预览**；程序内部依次调用 **`install_packages` → `materialize_workspace` → 工作区 `install-workspace-editables`（四轮 pip）→ 暂停并提示用编辑器打开工作区 `.env` → `run_doctor` → `probe --no-http`（进程内）**（与现行 `bootstrap/README.md` 一致）。**`feishu-onboard`**、**`VLA_WORKSPACE_ROOT`**、起 Redis/webhook 仍为人工或脚本后续步（交互里须打印简短提醒，不强行塞进同一子进程）。

**与分立子命令关系：** `doctor` / `install-packages` / `materialize-workspace` **不**单独构成与人验收等价的入口；README 与 spec §7 均以 **上述 1→2→3** 为签字路径。文末「分步命令」**仅**供自动化、CI、开发排障对照，**非**验收替代路径。

**展开：** 人机验收逐步操作口径见下文 **「用户验收主流程（签字用）」** 内 **「人工验收操作路径（展开说明）」**。

---

## 文件结构（落地前总览）

| 路径 | 职责 |
|------|------|
| `bootstrap/pyproject.toml` | 包元数据、`requires-python >=3.12`、console_script `bootstrap` |
| `bootstrap/README.md` | §2.1 推荐流水线、§3.2 路径约定、交接清单、与 `BugList`/webhook 真源说明；**Task 14** 增补「无人介入验收」与签字路径对照 |
| `bootstrap/scripts/run-unattended-acceptance.ps1` | **Task 14（必交付）：** 落地后无人介入验收闸门；路径与 `.env` 均由 **本仓库** 推导/样本构造；**非** P0 人机签字替代 |
| `bootstrap/src/bootstrap/__init__.py` | 版本串（可选） |
| `bootstrap/src/bootstrap/cli.py` | `argparse` 分发：`interactive-setup`（**验收主入口**）+ `doctor` / `install-packages` / `materialize-workspace`（CI/排障） |
| `bootstrap/src/bootstrap/interactive_setup.py` | **Task 13（P0）**：`run_interactive_setup()`，stdin 提示 + 调用既有 install/materialize/doctor API（无重复业务逻辑） |
| `bootstrap/src/bootstrap/paths.py` | 默认 **克隆根**（`parents[3]`）+ **`assert_clone_root_looks_sane`**（缺 `webhook/pyproject.toml` 则报错、提示 `--clone-root`；wheel 安装必显式传参） |
| `bootstrap/src/bootstrap/env_dotenv.py` | 轻量读 **工作区根** `.env`：`REDIS_URL`、`FOLDER_ROUTES_FILE` 等（忽略注释行）；**不**依赖路径类键 |
| `bootstrap/src/bootstrap/workspace_path.py` | §3.2 路径段 ASCII/禁字符校验；克隆根与工作区 **互不嵌套** |
| `bootstrap/src/bootstrap/routing_json.py` | 读 JSON → `pipeline_workspace.path`，**仅**供与 **`Path(--workspace)`** 漂移 WARNING（非门禁） |
| `.env.example`（仓库根，模板） | 注释说明：**物化后文件位于工作区根**，工作区路径 **仅**由 `bootstrap --workspace` 指定，**勿**增加 `PIPELINE_WORKSPACE_PATH` |
| `bootstrap/src/bootstrap/copy_trees.py` | 物化递归拷贝 + ignore（**已替代** 历史 `junction.py`） |
| `bootstrap/src/bootstrap/materialize.py` | §3.4 物化：实拷贝 **`vla_env_contract`**、**`runtime/webhook`**、**`tools/*`**（**不**写路径重复键） |
| `bootstrap/src/bootstrap/doctor.py` | §5.1 自检聚合、退出码 |
| `bootstrap/src/bootstrap/install_packages.py` | 对四子包 `pip install -e` + `pip install markitdown` |
| `bootstrap/tests/test_cli.py` | Task 1 / Task 13：`--help`、入口冒烟 |
| `bootstrap/tests/test_workspace_path.py` | 纯函数路径校验 |
| `bootstrap/tests/test_paths.py` | 克隆根推导、`assert_clone_root_looks_sane` |
| `bootstrap/tests/test_env_dotenv.py` | `.env` 解析 |
| `bootstrap/tests/test_routing_json.py` | JSON 提取 |
| `bootstrap/tests/test_materialize.py` | 物化目录树（实拷贝、**`runtime/webhook`**、TOML 路径修补） |
| `bootstrap/tests/test_probe.py` | `bootstrap probe` 静态段 / HTTP 段（mock） |
| `bootstrap/tests/test_install_packages.py` | mock `pip` 调用链 |
| `bootstrap/tests/test_doctor.py` | mock `redis`、mock `shutil.which`、临时目录 |
| `bootstrap/tests/test_interactive_setup.py` | Task 13：mock `input`、调用顺序 |
| `webhook/操作手册.md` | 增加「生产/bootstrap」互链；**`VLA_WORKSPACE_ROOT` + 工作区 `.env`** 启动约定 |
| `webhook/阶段性验收手册.md` | **Task 12** 同步修订：「根 `.env`/仓库根」表述与 **`VLA_WORKSPACE_ROOT` + 工作区根 `.env`** 一致（与 `操作手册.md` 同口径） |
| `onboard/README.md` | **Task 10**：与双线 `.env`、`FEISHU_ONBOARD_REPO_ROOT`、工作区手工合并语义一致（避免读者以为只改克隆根即完成运行配置） |
| `webhook/src/webhook_cursor_executor/settings.py` | **`_env_file()`**：`VLA_WORKSPACE_ROOT` 设则读 `{该路径}/.env`，否则沿用克隆根 `.env`（dev）；`settings_customise_sources` 使路径在 **实例化** 时解析 |
| `webhook/tests/test_settings.py` | 覆盖 `VLA_WORKSPACE_ROOT` 与 dotenv 加载 |
| `docs/superpowers/samples/pipeline-workspace-root.env.example` | **可提交**：说明工作区 `.env` 约定；指向同目录真密钥样本 |
| `docs/superpowers/samples/pipeline-workspace-root.env` | **含真实密钥、已 `.gitignore`**：从本机克隆根 `.env` 同步的验证用工作区 `.env` 全文；**勿提交** |

---

## 验证用工作区 `.env` 样本（本 plan 引用）

- **结构说明（可提交）：** [`docs/superpowers/samples/pipeline-workspace-root.env.example`](../samples/pipeline-workspace-root.env.example)
- **真密钥副本（仅本地、gitignore）：** [`docs/superpowers/samples/pipeline-workspace-root.env`](../samples/pipeline-workspace-root.env) — `QA_RULE_FILE` 已用 `rules/`；`FOLDER_ROUTES_FILE` 为克隆根 JSON 绝对路径；与 **工作区根** `.env` 或维护仓库种子漂移时，以 **当前运行真源（工作区根 `.env`）** 为准重生成或手工合并。
- **用法：** `materialize-workspace` 后 `Copy-Item` 该文件到 `{WORKSPACE}\.env`（PowerShell `-Encoding utf8`）；`$env:VLA_WORKSPACE_ROOT` = 同 `--workspace`。
- **维护：** 更新 **工作区或维护仓库种子** 后按需刷新 `pipeline-workspace-root.env`；合并前确认该路径仍在 `.gitignore`。

---

### Task 1: `bootstrap/pyproject.toml` 与包骨架

**Files:**
- Create: `bootstrap/pyproject.toml`
- Create: `bootstrap/src/bootstrap/__init__.py`
- Create: `bootstrap/src/bootstrap/cli.py`

- [ ] **Step 1: 写失败测试（入口可调用）**

Create: `bootstrap/tests/test_cli.py`

```python
import subprocess
import sys
from pathlib import Path


def test_bootstrap_module_invokable():
    cli = Path(__file__).resolve().parents[1] / "src" / "bootstrap" / "cli.py"
    r = subprocess.run([sys.executable, str(cli), "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "doctor" in r.stdout
```

**顺序约束（勿倒置）：** Task 1 **仅**校验 `--help` 成功且输出含已有子命令（如 **`doctor`**）。**不得**在本步断言 **`interactive-setup`**：`interactive-setup` 子命令 **Task 13** 才注册；对其与 **`bootstrap --help`** 的断言放在 **Task 13 Step 1**（与本步扩充 `test_cli.py` 同步），否则 Task 1 会先失败或被迫假绿。

- [ ] **Step 2: 运行测试，确认失败（模块未建）**

Run: 在 **`<CLONE_ROOT>`**（维护仓库根）下执行：`python -m pytest bootstrap\tests\test_cli.py::test_bootstrap_module_invokable -v`

Expected: `FAIL`（找不到 `cli.py` 或 returncode != 0）

- [ ] **Step 3: 添加 `pyproject.toml` 与最小 `cli.py`**

`bootstrap/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "newvla-production-bootstrap"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "redis>=6.0,<7.0",
]
[project.scripts]
bootstrap = "bootstrap.cli:main"

[project.optional-dependencies]
test = [
  "pytest>=8.3,<9.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`bootstrap/src/bootstrap/__init__.py`:

```python
__version__ = "0.1.0"
```

`bootstrap/src/bootstrap/cli.py`:

```python
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bootstrap")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="环境自检")
    sub.add_parser("install-packages", help="pip install -e 子包 + markitdown")
    sub.add_parser("materialize-workspace", help="物化执行工作区")
    ns = p.parse_args(argv)
    if ns.cmd == "doctor":
        return 0
    if ns.cmd == "install-packages":
        return 0
    if ns.cmd == "materialize-workspace":
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 再跑同一测试**

Run: `python -m pytest bootstrap\tests\test_cli.py::test_bootstrap_module_invokable -v`

Expected: `PASS`

- [ ] **Step 5: 提交**

```powershell
Set-Location <CLONE_ROOT>
git add bootstrap/pyproject.toml bootstrap/src/bootstrap/__init__.py bootstrap/src/bootstrap/cli.py bootstrap/tests/test_cli.py
git commit -m "feat(bootstrap): scaffold package and CLI stub"
```

---

### Task 2: `workspace_path.py`（§3.2 + 互不嵌套）

**Files:**
- Create: `bootstrap/src/bootstrap/workspace_path.py`
- Create: `bootstrap/tests/test_workspace_path.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from pathlib import Path

from bootstrap.workspace_path import validate_workspace_root_path


def test_rejects_non_ascii_segment():
    p = Path(r"C:\example\ascii-workspace-root")
    validate_workspace_root_path(p)  # OK

    bad = Path(r"C:\example\工作区\bad")
    with pytest.raises(ValueError, match="ASCII"):
        validate_workspace_root_path(bad)


def test_rejects_space_in_segment():
    bad = Path(r"C:\example\new vla\workspace")
    with pytest.raises(ValueError):
        validate_workspace_root_path(bad)


def test_rejects_nested_workspace_under_clone():
    clone = Path(r"C:\example\repo")
    ws = Path(r"C:\example\repo\sub\workspace")
    with pytest.raises(ValueError, match="nested"):
        validate_workspace_root_path(ws, clone_root=clone)
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python -m pytest bootstrap\tests\test_workspace_path.py -v`

Expected: `FAIL`（ImportError 或行为未实现）

- [ ] **Step 3: 实现**

`bootstrap/src/bootstrap/workspace_path.py`:

```python
from __future__ import annotations

import string
from pathlib import Path

_ALLOWED_EXTRA = frozenset("-_")


def _segment_ok(name: str) -> bool:
    if not name or not all((c in string.ascii_letters or c in string.digits or c in _ALLOWED_EXTRA) for c in name):
        return False
    return True


def validate_workspace_root_path(path: Path, *, clone_root: Path | None = None) -> Path:
    resolved = path.expanduser()
    if not resolved.is_absolute():
        raise ValueError("workspace root must be absolute path")
    parts = resolved.parts
    for seg in parts:
        if seg in ("/", "\\") or len(seg) == 2 and seg.endswith(":"):
            continue
        if not _segment_ok(seg):
            raise ValueError(
                f"workspace path segment must be ASCII letters/digits/hyphen/underscore only: {seg!r}"
            )
    if clone_root is not None:
        cr = clone_root.resolve()
        wr = resolved.resolve()
        try:
            wr.relative_to(cr)
            raise ValueError("workspace root must not be nested under clone root")
        except ValueError as e:
            if "nested" in str(e).lower() or "must not be nested" in str(e):
                raise
        try:
            cr.relative_to(wr)
            raise ValueError("clone root must not be nested under workspace root")
        except ValueError:
            pass
    return resolved
```

**实现注意：** `Path.relative_to` 在前后缀不满足嵌套关系时也会抛出 **`ValueError`**，文案未必含 **`nested`**。实现嵌套校验时应使用 **`Path.is_relative_to`**（Python 3.12+）或对 **`parts`** 做前缀判定，**勿**仅靠 `except ValueError` 后匹配字符串 **`"nested"`**，以免误判「工作区不在克隆根下」的正常情形。

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest bootstrap\tests\test_workspace_path.py -v`

Expected: 全部 `PASS`

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/src/bootstrap/workspace_path.py bootstrap/tests/test_workspace_path.py
git commit -m "feat(bootstrap): validate workspace path per spec §3.2"
```

---

### Task 3: `env_dotenv.py`

**Files:**
- Create: `bootstrap/src/bootstrap/env_dotenv.py`
- Create: `bootstrap/tests/test_env_dotenv.py`

- [ ] **Step 1: 写测试**

```python
from pathlib import Path

from bootstrap.env_dotenv import read_env_keys


def test_read_env_keys(tmp_path):
    p = tmp_path / ".env"
    p.write_text(
        "# x\nREDIS_URL=redis://localhost:6379/0\n"
        "FOLDER_ROUTES_FILE=webhook/config/routes.json\n",
        encoding="utf-8",
    )
    keys = read_env_keys(p)
    assert keys["REDIS_URL"] == "redis://localhost:6379/0"
    assert keys["FOLDER_ROUTES_FILE"] == "webhook/config/routes.json"
```

- [ ] **Step 2: 运行失败**

Run: `python -m pytest bootstrap\tests\test_env_dotenv.py -v`

Expected: `FAIL`

- [ ] **Step 3: 实现**

`bootstrap/src/bootstrap/env_dotenv.py`:

```python
from __future__ import annotations

from pathlib import Path


def read_env_keys(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out
```

- [ ] **Step 4: 测试通过**

Run: `python -m pytest bootstrap\tests\test_env_dotenv.py -v`

Expected: `PASS`

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/src/bootstrap/env_dotenv.py bootstrap/tests/test_env_dotenv.py
git commit -m "feat(bootstrap): parse workspace root .env keys"
```

---

### Task 4: `routing_json.py`（漂移告警专用，非门禁）

**Files:**
- Create: `bootstrap/src/bootstrap/routing_json.py`
- Create: `bootstrap/tests/test_routing_json.py`

**说明：** 与 `BugList.md` BUG-005 一致：**合同在工作区根 `.env`**；工作区物理路径以 **`--workspace`** 为准。本模块只解析 JSON，供 `doctor` 在 **`pipeline_workspace.path` 与 `Path(--workspace)` 不一致时** 打 WARNING；**不得**用 JSON 结果决定 `doctor` 是否通过。

- [ ] **Step 1: 写测试**

```python
import json
from pathlib import Path

from bootstrap.routing_json import load_pipeline_workspace_path_from_json


def test_load_pipeline_workspace_path_from_json(tmp_path):
    j = tmp_path / "r.json"
    j.write_text(
        json.dumps({"pipeline_workspace": {"path": "D:\\\\a\\\\b", "cursor_timeout_seconds": 1}}),
        encoding="utf-8",
    )
    assert load_pipeline_workspace_path_from_json(j) == r"D:\\a\\b"
```

- [ ] **Step 2: 运行失败**

Run: `python -m pytest bootstrap\tests\test_routing_json.py -v`

Expected: `FAIL`

- [ ] **Step 3: 实现**

`bootstrap/src/bootstrap/routing_json.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


def load_pipeline_workspace_path_from_json(routes_file: Path) -> str:
    data = json.loads(routes_file.read_text(encoding="utf-8"))
    try:
        return str(data["pipeline_workspace"]["path"])
    except (KeyError, TypeError) as e:
        raise ValueError(f"invalid routing JSON: missing pipeline_workspace.path: {e}") from e
```

- [ ] **Step 4: 测试通过**

Run: `python -m pytest bootstrap\tests\test_routing_json.py -v`

Expected: `PASS`

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/src/bootstrap/routing_json.py bootstrap/tests/test_routing_json.py
git commit -m "feat(bootstrap): parse routing JSON for drift warning only"
```

---

### Task 5: `paths.py`（默认克隆根）

**Files:**
- Create: `bootstrap/src/bootstrap/paths.py`
- Create: `bootstrap/tests/test_paths.py`

- [ ] **Step 1: 写测试**

```python
from pathlib import Path

from bootstrap import paths


def test_default_clone_root_is_repo_root():
    cr = paths.default_clone_root()
    assert (cr / "webhook" / "pyproject.toml").is_file()
    assert (cr / "bootstrap" / "pyproject.toml").is_file()
```

- [ ] **Step 2: 运行失败**

Run: `python -m pytest bootstrap\tests\test_paths.py -v`

Expected: `FAIL`

- [ ] **Step 3: 实现**

`bootstrap/src/bootstrap/paths.py`:

```python
from __future__ import annotations

from pathlib import Path


def default_clone_root() -> Path:
    return Path(__file__).resolve().parents[3]
```

**实现注意（`default_clone_root` 失效场景）：**

- **`pip install -e ./bootstrap`** 且包内 `__file__` 仍在克隆树下 → `parents[3]` 指向仓库根，**可用**。
- **`pip install` wheel / 仅装到 `site-packages`** → `__file__` 不在克隆树，`parents[3]` **错位**。**必须**显式传 **`--clone-root`**。
- **CLI 约束：** `materialize-workspace` / `install-packages` / `doctor` 在调用 `default_clone_root()` 后执行 **`assert_clone_root_looks_sane(root: Path) -> Path`**：若 **`(root / "webhook" / "pyproject.toml").is_file()`** 且 **`(root / "bootstrap" / "pyproject.toml").is_file()`** 才通过；否则 **非零退出**，stderr 说明：请 **`--clone-root <本仓库克隆绝对路径>`**（或改用可编辑安装）。单测：对临时目录调用 `assert_clone_root_looks_sane` → `SystemExit` 或 `ValueError`。

- [ ] **Step 4: 测试通过**

Run: `python -m pytest bootstrap\tests\test_paths.py -v`

Expected: `PASS`

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/src/bootstrap/paths.py bootstrap/tests/test_paths.py
git commit -m "feat(bootstrap): resolve default clone root from package location"
```

---

### Task 6: `junction.py`（Windows）

**Files:**
- Create: `bootstrap/src/bootstrap/junction.py`

- [ ] **Step 1: 写测试（非 Windows 跳过）**

Create: `bootstrap/tests/test_junction.py`

```python
import os
import sys
from pathlib import Path

import pytest

from bootstrap import junction


@pytest.mark.skipif(sys.platform != "win32", reason="junctions are Windows P0")
def test_ensure_junction_creates_link(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "x.txt").write_text("hi", encoding="utf-8")
    link = tmp_path / "link"
    junction.ensure_junction(link, target)
    assert link.is_dir()
    assert (link / "x.txt").read_text(encoding="utf-8") == "hi"
```

- [ ] **Step 2: 运行（Windows 上应失败直至实现）**

Run: `python -m pytest bootstrap\tests\test_junction.py -v`

Expected: 非 Windows `SKIPPED`；Windows `FAIL` 直至实现

- [ ] **Step 3: 实现**

`bootstrap/src/bootstrap/junction.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def ensure_junction(link: Path, target: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("junction strategy requires Windows (spec P0)")
    target_r = target.resolve()
    if not target_r.is_dir():
        raise FileNotFoundError(f"junction target must exist: {target_r}")
    if link.exists():
        if not link.is_dir():
            raise FileExistsError(f"path exists and is not a directory: {link}")
        # Windows 上目录联接经 Path.resolve() 会解析到目标目录；普通目录则解析为自身。
        if link.resolve() == target_r:
            return
        raise FileExistsError(
            f"path exists and resolves to {link.resolve()!s}, not junction target {target_r!s}: {link}"
        )
    link.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target_r)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "mklink /J failed:\n"
            + (proc.stderr or proc.stdout or "").strip()
        )
```

**说明：** **不**解析 reparse tag / `st_file_attributes`（版本与实现差异大）。已存在路径：**仅**用 `is_dir` + `resolve() == target_r` 判定是否与目标一致；新建：**仅**以 `mklink /J` 退出码与非零时 stderr/stdout 报错为准。边界与回归靠 `test_junction.py` + `test_materialize_tools_junctions`。

- [ ] **Step 4: Windows 上测试通过**

Run: `python -m pytest bootstrap\tests\test_junction.py -v`

Expected: `PASS` 或 `SKIPPED`

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/src/bootstrap/junction.py bootstrap/tests/test_junction.py
git commit -m "feat(bootstrap): Windows directory junction helper"
```

---

### Task 7: `materialize.py`

**Files:**
- Create: `bootstrap/src/bootstrap/materialize.py`
- Modify: `bootstrap/src/bootstrap/cli.py`（挂接子命令参数）

- [ ] **Step 1: 写测试（工作区 `.env` 种子 + 规则树，junction 跳过）**

Create: `bootstrap/tests/test_materialize.py`

```python
import sys
from pathlib import Path

import pytest

from bootstrap.materialize import materialize_workspace


def _minimal_clone(clone: Path, env_example_body: str) -> None:
    (clone / ".env.example").write_text(env_example_body, encoding="utf-8")
    prompts = clone / "prompts"
    rules = prompts / "rules" / "qa"
    rules.mkdir(parents=True)
    (rules / "x.mdc").write_text("rule", encoding="utf-8")
    (prompts / "AGENTS.txt").write_text("agents", encoding="utf-8")


def test_materialize_seeds_workspace_env_from_clone_dotenv_when_present(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "FROM_EXAMPLE=only\n")
    (clone / ".env").write_text("FROM_CLONE=1\n", encoding="utf-8")
    materialize_workspace(
        clone_root=clone,
        workspace_root=ws,
        link_tools=sys.platform == "win32",
        seed_env=None,
    )
    assert (ws / ".env").read_text(encoding="utf-8") == "FROM_CLONE=1\n"


def test_materialize_seeds_workspace_env_from_dotenv_example_when_no_clone_dotenv(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "K=v\n")
    materialize_workspace(
        clone_root=clone,
        workspace_root=ws,
        link_tools=sys.platform == "win32",
        seed_env=None,
    )
    assert (ws / ".env").read_text(encoding="utf-8") == "K=v\n"
    assert (ws / "AGENTS.md").read_text(encoding="utf-8") == "agents"
    assert (ws / "rules" / "qa" / "x.mdc").read_text(encoding="utf-8") == "rule"
    assert (ws / ".cursor_task").exists() is False


def test_materialize_does_not_overwrite_existing_workspace_env(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "FROM_TEMPLATE=1\n")
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".env").write_text("KEEP=secret\n", encoding="utf-8")
    materialize_workspace(clone_root=clone, workspace_root=ws, link_tools=False, seed_env=None)
    assert (ws / ".env").read_text(encoding="utf-8") == "KEEP=secret\n"


@pytest.mark.skipif(sys.platform != "win32", reason="tools junction only on win")
def test_materialize_tools_junctions(tmp_path):
    clone = tmp_path / "clone"
    (clone / "dify_upload" / "src").mkdir(parents=True)
    (clone / "feishu_fetch" / "src").mkdir(parents=True)
    (clone / ".env.example").write_text("x=1\n", encoding="utf-8")
    (clone / "prompts" / "AGENTS.txt").write_text("a", encoding="utf-8")
    (clone / "prompts" / "rules").mkdir(parents=True)
    ws = tmp_path / "ws"
    materialize_workspace(clone_root=clone, workspace_root=ws, link_tools=True, seed_env=None)
    assert (ws / "tools" / "dify_upload" / "src").is_dir()
```

- [ ] **Step 2: 运行失败**

Run: `python -m pytest bootstrap\tests\test_materialize.py -v`

Expected: `FAIL`

- [ ] **Step 3: 实现 `materialize_workspace`**

`bootstrap/src/bootstrap/materialize.py`:

```python
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from bootstrap.junction import ensure_junction
from bootstrap.workspace_path import validate_workspace_root_path


def materialize_workspace(
    *,
    clone_root: Path,
    workspace_root: Path,
    link_tools: bool,
    seed_env: Path | None = None,
    sync_env_from_clone: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    validate_workspace_root_path(workspace_root, clone_root=clone_root)
    workspace_root.mkdir(parents=True, exist_ok=True)
    env_dst = workspace_root / ".env"
    clone_env = clone_root / ".env"
    # 工作区 .env：spec §2.1 — 首次（1）克隆根 .env（2）否则 --seed-env（3）否则 .env.example
    # --sync-env-from-clone：从维护仓覆盖工作区 .env（spec §2.1 条 6）
    if sync_env_from_clone:
        if not clone_env.is_file():
            raise FileNotFoundError(f"sync_env_from_clone but missing {clone_env}")
        if not dry_run:
            shutil.copy2(clone_env, env_dst)
    elif not env_dst.is_file():
        if clone_env.is_file():
            if not dry_run:
                shutil.copy2(clone_env, env_dst)
        elif seed_env is not None:
            if not seed_env.is_file():
                raise FileNotFoundError(f"seed_env is not a file: {seed_env}")
            if not dry_run:
                shutil.copy2(seed_env, env_dst)
        else:
            tmpl = clone_root / ".env.example"
            if not tmpl.is_file():
                raise SystemExit(
                    "工作区尚无 .env，且克隆根缺少 .env、.env.example 且无 --seed-env；无法创建工作区根运行合同 .env（见 bootstrap/README.md）"
                )
            if not dry_run:
                shutil.copy2(tmpl, env_dst)
    agents_src = clone_root / "prompts" / "AGENTS.txt"
    if not agents_src.is_file():
        raise FileNotFoundError(f"missing {agents_src}")
    rules_src = clone_root / "prompts" / "rules"
    rules_dst = workspace_root / "rules"
    if rules_dst.exists() and any(rules_dst.iterdir()) and not force and not dry_run:
        raise SystemExit("工作区 rules/ 已存在且非空；请加 --force 或先备份（见 bootstrap/README.md）")
    if dry_run:
        return
    shutil.copy2(agents_src, workspace_root / "AGENTS.md")
    if rules_dst.exists():
        shutil.rmtree(rules_dst)
    shutil.copytree(rules_src, rules_dst)
    tools = workspace_root / "tools"
    tools.mkdir(exist_ok=True)
    if link_tools and sys.platform == "win32":
        ensure_junction(tools / "dify_upload", clone_root / "dify_upload")
        ensure_junction(tools / "feishu_fetch", clone_root / "feishu_fetch")
    elif link_tools:
        raise RuntimeError("link_tools requires Windows")
    else:
        (tools / "dify_upload").mkdir(exist_ok=True)
        (tools / "feishu_fetch").mkdir(exist_ok=True)
```

（验收：P0 Windows 下 `link_tools=True`；测试在非 Windows 用 `link_tools=False` 走 mkdir 分支可在 `cli` 层根据平台默认。）

**破坏性操作与幂等（覆盖 `rules/`、`AGENTS.md`）：**

- 代码块已体现：**非空** `rules/` 且无 `--force`、非 `dry_run` → **退出**；**`--dry-run`** 在校验后 **`return`**，**不写盘** —— **不**满足 spec §3.4「物化产物已持久落盘」的验收，仅运维预览。README 须写物化前备份与 **`--sync-env-from-clone`** 用途。

- [ ] **Step 4: `cli.py` 挂接**

在 `materialize-workspace` 解析 `--clone-root`（默认 `paths.default_clone_root()`，**须经** `assert_clone_root_looks_sane`，见 Task 5）、`--workspace`（必填）、**`--sync-env-from-clone`**（用克隆根 `.env` 覆盖工作区 `.env`，spec §2.1 条 6）、`--seed-env`（可选：**仅当**克隆根 **无** `.env` 时进入回退链，与 `.env.example` 并列；克隆根有 `.env` 时 **忽略**）、`--no-junction-tools`、`--dry-run`、`--force`。

- [ ] **Step 5: 测试通过**

Run: `python -m pytest bootstrap\tests\test_materialize.py -v`

Expected: `PASS` / `SKIPPED`

- [ ] **Step 6: 提交**

```powershell
git add bootstrap/src/bootstrap/materialize.py bootstrap/src/bootstrap/cli.py bootstrap/tests/test_materialize.py
git commit -m "feat(bootstrap): materialize workspace per spec §3.4"
```

---

### Task 8: `install_packages.py`

**Files:**
- Create: `bootstrap/src/bootstrap/install_packages.py`
- Modify: `bootstrap/src/bootstrap/cli.py`

- [ ] **Step 1: 写测试（mock subprocess）**

Create: `bootstrap/tests/test_install_packages.py`

```python
from pathlib import Path
from unittest.mock import patch

from bootstrap.install_packages import install_all


def test_install_all_invokes_pip(tmp_path):
    clone = tmp_path / "c"
    for name in ("webhook", "onboard", "dify_upload", "feishu_fetch"):
        p = clone / name
        p.mkdir(parents=True)
        (p / "pyproject.toml").write_text("[project]\nname=dummy\nversion=0\n", encoding="utf-8")
    recorded: list[list[str]] = []

    def fake_run(cmd, check=True):
        recorded.append(cmd)
        return 0

    with patch("bootstrap.install_packages._pip_run", fake_run):
        install_all(clone)
    assert any("webhook" in str(x) for x in recorded)
    assert any("markitdown" in str(x) for x in recorded)
```

- [ ] **Step 2: 运行失败**

Run: `python -m pytest bootstrap\tests\test_install_packages.py -v`

Expected: `FAIL`

- [ ] **Step 3: 实现**

`bootstrap/src/bootstrap/install_packages.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_EDITABLE_PACKAGES = ("webhook", "onboard", "dify_upload", "feishu_fetch")


def _pip_run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "pip", *args], check=True)


def install_all(clone_root: Path) -> None:
    for name in _EDITABLE_PACKAGES:
        pkg = clone_root / name
        if not (pkg / "pyproject.toml").is_file():
            raise FileNotFoundError(f"missing package: {pkg}")
        _pip_run(["install", "-e", str(pkg)])
    _pip_run(["install", "markitdown"])
```

- [ ] **Step 4: 测试通过**

Run: `python -m pytest bootstrap\tests\test_install_packages.py -v`

Expected: `PASS`

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/src/bootstrap/install_packages.py bootstrap/tests/test_install_packages.py bootstrap/src/bootstrap/cli.py
git commit -m "feat(bootstrap): install-packages editable + markitdown"
```

---

### Task 9: `doctor.py`

**Files:**
- Create: `bootstrap/src/bootstrap/doctor.py`
- Create: `bootstrap/tests/test_doctor.py`
- Modify: `bootstrap/src/bootstrap/cli.py`

- [ ] **Step 1: 写测试**

实现时在 `doctor.py` 为 markitdown 提供薄封装 **`_import_markitdown()`**（内部 `importlib.import_module("markitdown")`），便于单测 patch、避免全局 stub `import_module` 误伤子包 import。

```python
from pathlib import Path
from unittest.mock import MagicMock, patch

from bootstrap.doctor import run_doctor


def test_doctor_fails_without_markitdown(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("K=v\n", encoding="utf-8")
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\cursor"):
        with patch("bootstrap.doctor._import_markitdown", side_effect=ImportError("no")):
            code = run_doctor(clone_root=clone, workspace=ws)
    assert code != 0


def test_doctor_ok_minimal_mocks(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("K=v\n", encoding="utf-8")
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):  # no-op
                with patch("bootstrap.doctor.redis.from_url") as fr:
                    fr.return_value.ping.return_value = True
                    code = run_doctor(clone_root=clone, workspace=ws)
    assert code == 0
```

（`_import_pipeline_packages` 为实现时抽出的「依次 import 四包」函数；测试中 patch 为空操作即可。第二则测试不覆盖 JSON 漂移；可另增用例。）

约定：`run_doctor(clone_root: Path, workspace: Path)`；**无** `REDIS_URL` 则跳过 ping（与 §2.1 分档一致）；有则失败返回 1。

- [ ] **Step 2: 运行失败**

Run: `python -m pytest bootstrap\tests\test_doctor.py -v`

Expected: `FAIL`

- [ ] **Step 3: 实现 `run_doctor`**

要点（对照规格）：

1. `sys.version_info < (3, 12)` → 打印错误，返回 1。
2. `shutil.which("cursor")` 与 `shutil.which("lark-cli")` 缺失 → 打印错误，返回 1。
3. **`_import_markitdown()`**（内部 `import_module("markitdown")`）失败 → 打印可复制 `python -m pip install markitdown`，返回 1。
4. 对 `feishu_fetch`、`dify_upload`、`webhook_cursor_executor`、`feishu_onboard` 依次 `import_module`，失败则打印缺失包与 `pip install -e` 提示，返回 1。
5. **`{workspace}/.env` 不存在** → 返回 1，提示先 `materialize-workspace`（或 `--seed-env`）生成 **工作区根** `.env`。
6. **工作区** `.env` 含 `REDIS_URL` → `redis.from_url(url).ping()`，失败返回 1；**无该键**则跳过 Redis 项并明示（与 §2.1 弱化分档一致）。
7. `validate_workspace_root_path(workspace, clone_root=clone_root)`（CLI 传入的 `workspace` 与物化目标一致）。
8. **漂移告警（stderr）**：若 `FOLDER_ROUTES_FILE` 在工作区 `.env` 中且解析为可读 JSON（路径相对 **克隆根** 或绝对，算法在实现里写死并文档化），`load_pipeline_workspace_path_from_json` 与 **`Path(workspace).resolve()`**（`os.path.normcase`）不一致 → **WARNING**（BUG-005 / webhook 仍读 JSON）。
9. 标准输出末尾附 **简短** 债说明：BUG-004；BUG-005 修复方向见 BugList（JSON 与「`--workspace` 表达的工作区根」双写直至 webhook 收敛）。

`bootstrap/src/bootstrap/doctor.py` 由实现者写完整函数体（本计划不省略逻辑行，避免占位；实现时保持单函数 < 120 行，可拆 `_check_python` 等私有函数）。

- [ ] **Step 4: 测试通过**

Run: `python -m pytest bootstrap\tests\test_doctor.py -v`

Expected: `PASS`

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/src/bootstrap/doctor.py bootstrap/tests/test_doctor.py bootstrap/src/bootstrap/cli.py
git commit -m "feat(bootstrap): doctor checks per spec §5.1"
```

---

### Task 10: `bootstrap/README.md` 与 `webhook/操作手册.md` 互链

**Files:**
- Create: `bootstrap/README.md`
- Modify: `webhook/操作手册.md`
- Modify: `webhook/阶段性验收手册.md`（与 Task 12 同一文档口径：**Task 10** 可与操作手册一并修订，或留待 **Task 12 Step 4** 集中改；落地前须有一处覆盖）
- Modify: `onboard/README.md`（与上文「真源口径」条 3、`FEISHU_ONBOARD_REPO_ROOT`、交接清单对齐；本 plan **不**改 `flow.py`）
- Modify: `.env.example`

- [ ] **Step 1: 撰写 `bootstrap/README.md`**

必含章节（中文）：

- **用户验收唯一路径：** `Set-Location` 克隆根 → `python -m pip install -e .\bootstrap`（或 `.\bootstrap[test]`）→ **`bootstrap interactive-setup`**，按提示输入路径；内部串联 `install-packages` → `materialize-workspace` → 提示编辑 **`{WORKSPACE}\.env`** → `doctor --workspace`（与 spec §2.1 一致）。**合同 `.env` 仅在工作区根**；物理路径以交互收集的 **工作区根** 与 **`--workspace` 等价** 为准。
- **分立子命令**（`doctor` / `install-packages` / `materialize-workspace`）：**仅** CI、脚本、排障；README 须写明 **不得**与人验收签字混为并列主流程。
- **路径形状：** 见 design spec §3.2 / §3.3（ASCII、与克隆根互不嵌套）；**不在 README 写死盘符**；工作区目录由 **客户/运维选定**，在 **`interactive-setup` 交互中键入**（与内调 `materialize` / `doctor` 的 `--workspace` 一致）。
- 命令示例（PowerShell，无 `&&`）：

```powershell
Set-Location <CLONE_ROOT>
python -m pip install -e .\bootstrap
bootstrap interactive-setup
# 按提示输入；物化后按提示用编辑器打开工作区 .env 填密钥，再继续 doctor
```

**排障/CI（非验收主路径）：** 须逐条调用 `install-packages`、`materialize-workspace`、`doctor` 时，见文末「分步命令附录」。

- **一页交接清单**：谁维护 **工作区根 `.env`**、**所有** `bootstrap`/文档中的工作区路径是否与 **`--workspace`** 一致、onboard 写克隆根后是否已 **同步进工作区 `.env`**、BUG-005 下 JSON 的 `pipeline_workspace.path` 是否与 **`--workspace`** 双写、`feishu-onboard` 不单独等于布线完成（§4.2）、`BugList.md` BUG-004/BUG-005
- **`feishu-onboard` 与工作区：** `FEISHU_ONBOARD_REPO_ROOT`（见 `onboard/`）仅改写 **维护仓库根** 下落点；**运行合同真源仍为 `{WORKSPACE}/.env`**。入轨写入克隆根 `.env` 后须 **手工合并或复制** 到工作区根 `.env`（本 plan **不**强制改 `flow.py` 双写；以交接清单与 `onboard/README.md` 说明为准）。
- **`--clone-root` / 安装方式：** 推荐 **`pip install -e ./bootstrap`**；若 wheel 安装或默认推导克隆根失败（缺 `webhook/pyproject.toml`），须显式 **`--clone-root <克隆绝对路径>`**（见 Task 5）。
- **物化安全：** 更新 `rules/`/`AGENTS.md` 须 **`--force`**；**`--sync-env-from-clone`** 单独同步维护仓 `.env` → 工作区；事前 **备份**；首跑可用 **`--dry-run`**（见 Task 7）。
- **P0 与 CI：** 生产签字以 **Windows 实机 + junction** 为准；Linux CI 绿 ≠ 生产就绪（见 Task 11）。
- **互链验证样本：** [`docs/superpowers/samples/pipeline-workspace-root.env.example`](../samples/pipeline-workspace-root.env.example) / [`pipeline-workspace-root.env`](../samples/pipeline-workspace-root.env)（见 plan 文前「验证用工作区 `.env` 样本」节）

- [ ] **Step 2: 修改仓库根 `.env.example`**

在「Webhook 执行器」分组附近增加（UTF-8）：

```dotenv
# 本文件经 materialize 复制到「执行工作区根」后使用；工作区绝对路径仅通过 bootstrap --workspace 传递，勿在此重复定义路径键
#
# 生产起 webhook/RQ 前须在进程环境中设置 VLA_WORKSPACE_ROOT=<同上绝对路径>（见 Task 12；勿依赖本文件自举该变量）
```

- [ ] **Step 3: 在 `webhook/操作手册.md` 靠前位置增加短节「生产部署与 bootstrap」**

链接到 `bootstrap/README.md`，说明：**与人验收签字**须按 README **唯一路径** `bootstrap interactive-setup` 走通至 `doctor`；**合同 `.env` 在工作区根**；进程须设 **`VLA_WORKSPACE_ROOT`**（与交互/物化所用工作区根同路径）使 **`ExecutorSettings` 加载该 `.env`**（见 **Task 12**）；未设时仅 dev 回退克隆根 `.env`；BUG-005 未关前 JSON 的 `pipeline_workspace.path` 须与该工作区根 **双写一致**。分立子命令仅 CI/排障，见 README。

- [ ] **Step 3b: 修订 `webhook/阶段性验收手册.md`（可与 Step 3 同批提交，或移交 Task 12 Step 4）**

将文中「根目录 `.env` / 仅以仓库根为准」等与 **生产** 验收相关的表述，与 **`VLA_WORKSPACE_ROOT` + 工作区根 `.env`**、`操作手册.md` 及本 plan **Task 12** 一致，避免现场按旧手册验收时与双线 `.env` 口径冲突。

- [ ] **Step 3c: 修订 `onboard/README.md`（可与 Step 3 同批提交）**

检视正文是否易被理解为「改维护仓根 `.env` 即完成运行配置」：须与 **运行合同真源 = 工作区根 `.env`**、`FEISHU_ONBOARD_REPO_ROOT`、`bootstrap/README.md` 交接清单中的 **手工合并/复制** 说明一致（见文件结构表与本节 **`feishu-onboard` 与工作区** bullet）。

- [ ] **Step 4: 无代码测试；人工通读 spec §7 勾选**

- [ ] **Step 5: 提交**

```powershell
git add bootstrap/README.md webhook/操作手册.md webhook/阶段性验收手册.md onboard/README.md .env.example
git commit -m "docs(bootstrap): README, env example workspace note, webhook cross-link"
```

---

### Task 11: 全量 pytest 与可编辑安装冒烟

- [ ] **Step 1: 安装 bootstrap 测试依赖**

Run:

```powershell
Set-Location <CLONE_ROOT>
python -m pip install -e ".\bootstrap[test]"
```

Expected: 成功

- [ ] **Step 2: 跑 bootstrap 测试**

Run: 仍在 **`<CLONE_ROOT>`** 下：`python -m pytest bootstrap\tests -v`

Expected: 全部 `PASS`（非 Windows 上 junction 相关 `SKIPPED`）

**合并闸门：** **`bootstrap`** 相关 PR 须 **`powershell -File .\bootstrap\scripts\run-unattended-acceptance.ps1 -SkipDoctor`** **`exit 0`**（Task 14 **A 档**）；与本条 pytest **互补**。全量 **`doctor`**（**B 档**）在维护机另行验证（见 Task 14）。

**验收矩阵（CI vs 生产）：** **人验签字** = **Windows 实机**上 **`pip install -e .\bootstrap[…]` + `bootstrap interactive-setup`** 走通至 **`doctor` 可解释退出**（含真实 junction）。**Linux/macOS CI** 仅覆盖纯函数、mock、`skipif` junction — **不等价**生产签字，禁止单凭绿 CI 替代上述路径。

- [ ] **Step 3: 冒烟（开发机有依赖时）**

可选：将 [`docs/superpowers/samples/pipeline-workspace-root.env`](../samples/pipeline-workspace-root.env) 复制到本机 `--workspace\.env`，并设 `VLA_WORKSPACE_ROOT` 与路径一致（见 plan 文前样本节）。

Run（`$WORKSPACE` 为客户/本机已选定的执行工作区根）：

```powershell
bootstrap doctor --workspace $WORKSPACE
```

Expected: 若本机路径/依赖不符，失败信息可读；修后可通过

- [ ] **Step 4: 提交（如有修复）**

---

### Task 12: Webhook `ExecutorSettings` 读工作区 `.env`（无 Gap）

**Files:**
- Modify: `webhook/src/webhook_cursor_executor/settings.py`
- Modify: `webhook/tests/test_settings.py`
- Modify: `bootstrap/README.md`（Task 10 若已写则补一句）
- Modify: `webhook/操作手册.md`（Task 10 若已写则补一句）
- Modify: `webhook/阶段性验收手册.md`（若 Task 10 Step 3b 未完成则本步补齐）
- Modify: `.env.example`（克隆根模板：说明 `VLA_WORKSPACE_ROOT`）

**约定：**
- **`VLA_WORKSPACE_ROOT`**：进程环境变量（或启动脚本在 **import `ExecutorSettings` 之前** 已写入 `os.environ`），值为与 **`bootstrap materialize-workspace --workspace`** **相同**的绝对路径。**不得**指望从「即将加载的」工作区 `.env` 里首次读出自身路径（循环依赖）。
- 已设置：`ExecutorSettings` 的 dotenv 文件 = **`Path(VLA_WORKSPACE_ROOT).resolve() / ".env"`**。
- 未设置：**兼容** 现有克隆根 `Path(__file__).parents[3] / ".env"`（本地 dev）。
- **`model_config`**：去掉静态 `env_file=str(_env_file())`（import 时只算一次会锁死路径）；改用 **`settings_customise_sources`** 注入 **`DotEnvSettingsSource(..., env_file=_env_file(), env_file_encoding="utf-8")`**，保证 **每次构造 `ExecutorSettings` 时** 重算 `_env_file()`。
- 测试前若用 **`get_executor_settings`**：**`get_executor_settings.cache_clear()`**，避免 lru_cache 跨用例污染。

**改前锚点（避免 pydantic-settings API 漂移）：**

- **现状文件：** `webhook/src/webhook_cursor_executor/settings.py` — `_env_file()` 约 **L12–13**（克隆根 `.env`）；`ExecutorSettings.model_config` 约 **L47–53**，静态 **`env_file=str(_env_file())`**。
- **依赖版本：** `webhook/pyproject.toml` 锁定 **`pydantic-settings>=2.9,<3.0`**。实现 **`settings_customise_sources` + `DotEnvSettingsSource`** 前，在目标 venv 执行 `python -c "import pydantic_settings as p; print(p.__version__)"` 与 [官方文档](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) 该 minor 版一致；若上游签名变更，以 **仓库已锁版本** 为准调整 import 路径（`pydantic_settings.sources`）。

- [ ] **Step 1: 写失败测试**

在 `webhook/tests/test_settings.py` 追加：

```python
def test_env_file_uses_vla_workspace_root(tmp_path, monkeypatch):
    from webhook_cursor_executor import settings as s

    ws = tmp_path / "workspace"
    ws.mkdir()
    env_f = ws / ".env"
    env_f.write_text("REDIS_URL=redis://from-workspace-env:9/0\n", encoding="utf-8")
    monkeypatch.setenv("VLA_WORKSPACE_ROOT", str(ws))
    s.get_executor_settings.cache_clear()
    st = s.ExecutorSettings()
    assert st.redis_url == "redis://from-workspace-env:9/0"
```

Run: `Set-Location <CLONE_ROOT>\webhook` 后：`python -m pytest tests\test_settings.py::test_env_file_uses_vla_workspace_root -v`  
Expected: `FAIL`（尚未改 `settings.py`）

- [ ] **Step 2: 实现 `settings.py`**

要点：
1. `_env_file()`：`os.environ.get("VLA_WORKSPACE_ROOT", "").strip()` 非空 → `Path(...).expanduser().resolve() / ".env"`；否则 **`Path(__file__).resolve().parents[3] / ".env"`**（与现 L12–13 语义一致）。
2. `ExecutorSettings.model_config` 保留 `env_file_encoding`、`extra`、`populate_by_name`；**删除** `env_file=...`。
3. 实现 **`settings_customise_sources`**（`BaseSettings` 子类上 `@classmethod`，签名以 **pydantic-settings 2.9.x** 为准），返回元组含 **`DotEnvSettingsSource(settings_cls, env_file=_env_file(), env_file_encoding="utf-8")`** 与默认 **`env_settings`、`file_secret_settings`**（从 `pydantic_settings.sources` import；合并前对照仓库 venv 中该包的 `sources` 模块导出）。
4. `validate_bounds` 里 `_raise_if_env_file_bans_cursor_cli_command(path=_env_file())` 保持不变语义（**动态**路径仍指向「当前应加载的那份 `.env`」）。

- [ ] **Step 3: 测试通过 + 全 webhook settings 测**

Run: `python -m pytest webhook\tests\test_settings.py -v`  
Expected: 全部 `PASS`

**Flaky 注意：** 若 CI 或本地并行跑测出现 **`VLA_WORKSPACE_ROOT`** 遗留污染（与 `get_executor_settings` / 直接构造 `ExecutorSettings` 交叉），可在 **`test_settings.py`** 用 **`autouse` fixture** 或各用例 **`monkeypatch.delenv`** 在前后清空该变量（按需；非必选）。

- [ ] **Step 4: 文档与 `.env.example`**

- **`bootstrap/README.md`：** 生产起 **uvicorn / RQ worker** 前必须设置 **`VLA_WORKSPACE_ROOT=<与 --workspace 相同>`**（Windows 服务「环境变量」、PowerShell 会话、或等价注入），与 **工作区根 `.env`** 对齐。
- **`webhook/操作手册.md`：** 同上；并写清 **未设置时** 仍读克隆根 `.env` 仅作本地 dev。
- **`webhook/阶段性验收手册.md`：** 与 Task 10 Step 3b / 上文双线 `.env` 口径一致（若尚未修订）。
- **克隆根 `.env.example`：** 增加注释块（UTF-8）说明 `VLA_WORKSPACE_ROOT` 含义；**勿**把该键塞进工作区 `.env` 指望单独靠它自举路径。

- [ ] **Step 5: 提交**

```powershell
git add webhook/src/webhook_cursor_executor/settings.py webhook/tests/test_settings.py bootstrap/README.md webhook/操作手册.md webhook/阶段性验收手册.md .env.example
git commit -m "feat(webhook): load .env from VLA_WORKSPACE_ROOT for pipeline workspace"
```

---

### Task 13: `bootstrap interactive-setup`（交互编排，**P0 / 用户验收唯一入口**）

**依赖：** Task 1–11 已提供可导入的 `install_packages`、`materialize_workspace`、`run_doctor` 及路径/克隆根校验。**无 Task 13 则 P0 与人验收不结案。**

**Files:**
- Create: `bootstrap/src/bootstrap/interactive_setup.py`
- Modify: `bootstrap/src/bootstrap/cli.py`（增加子命令 `interactive-setup`，无额外 flag 或仅 `--yes` 跳过非关键确认）
- Create: `bootstrap/tests/test_interactive_setup.py`（`unittest.mock.patch` 模拟 `builtins.input`，断言调用顺序与传入 `clone_root` / `workspace`）

**行为要点：**

1. 启动时打印简短说明（UTF-8 控制台）；**维护仓库根**：默认当前工作目录，若 `assert_clone_root_looks_sane` 失败则反复提示输入绝对路径直至通过或用户中断。
2. **执行工作区根**：必填，提示须满足 design §3.2；`validate_workspace_root_path` 失败则重试。
3. 可选交互：`--dry-run` 是否先跑一遍物化预览、`link_tools` 是否创建 junction（与 CLI 默认一致）。
4. 调用链：`install_packages`（或等价已封装函数）→ `materialize_workspace` → **stdout 明确写**：请编辑 `{workspace}\.env` → `input("按 Enter 继续 doctor…")` 或跳过若 `--yes` → `run_doctor`；**退出码**与最后一步 `doctor` 一致。
5. **不得**在交互模块内复制 junction/复制 rules 等逻辑；仅调 `materialize.py` / `doctor.py` / `install_packages.py` 已有入口。
6. **`bootstrap --help`** 须列出 **`interactive-setup`**，help 文案标明 **与人验收主入口**（spec §7-1）。

- [ ] **Step 1:** 失败测试（mock input + 断言子流程被调用）；并**于此步**扩充 `test_cli.py`：`--help` 输出须含 **`interactive-setup`**（与 **Task 1** 对照：Task 1 **故意不验**该项，见 Task 1「顺序约束」）。
- [ ] **Step 2:** 实现 `interactive_setup.py` + `cli` 注册
- [ ] **Step 3:** `pytest bootstrap/tests/test_interactive_setup.py -v`；`pytest bootstrap/tests/test_cli.py -v`
- [ ] **Step 4:** 更新 `bootstrap/README.md`：**验收唯一路径** = 理想交互三节 + `bootstrap interactive-setup`；分立子命令标注为 CI/排障
- [ ] **Step 5:** 提交 `feat(bootstrap): interactive-setup wizard`

---

### Task 14: 落地后无人介入验收（**必跑闸门**，脚本自动化）

**优先级：** **plan 收尾必备**（与 **Task 13 P0** 并行层级不同：Task 13 = 产品人机签字口径；Task 14 = **实现合理性回归闸门**）。**依赖 Task 1–13 已全部可用**。

**目的：** 代码 Task 落地后 **无人值守**跑通 **CLI 编排与物化**；**不因**缺失 **`cursor`/`lark-cli`/Redis** 等外部环境而让 merge **误判失败**。本链条 **仍不**替代 **Task 13 / 人机签字**（README 须写明）。

**闸门分两档（避免把「闸门」绑死在 `doctor` 全量外部环境上）：**

| 档位 | 步骤 | 适用 |
|------|------|------|
| **A（必选 / merge 最低门槛）** | **`pip install -e .\bootstrap[test]`** → **`bootstrap install-packages`** → **`bootstrap materialize-workspace …`** → **`Copy-Item`** **`docs\superpowers\samples\pipeline-workspace-root.env.example`** **覆盖** **`{WORKSPACE}\.env`** | **PR / CI**：脚本参数 **`-SkipDoctor`**（或等价开关）时 **仅执行到此**，成功则 **`exit 0`**。验证 **`materialize`** 已创建目录树且 **`.env`/`AGENTS.md`**（或与 Task 7 一致的产物）可读即可（脚本可用 **`Test-Path`** 自检）。 |
| **B（默认全量 / 维护机）** | A + **`bootstrap doctor --workspace $WORKSPACE`** | **依赖 Task 9**：需 **`cursor`、`lark-cli`、`markitdown`**、四包已 **`install-packages`**、可选 Redis；**无 `-SkipDoctor`** 时执行；失败视为 **环境与实现问题须区分**（stderr 已有提示）。 |

**输入构造原则（全部由本仓库现状推导，勿依赖外来机密）：**

| 输入 | 构造规则 |
|------|----------|
| **克隆根 `<CLONE_ROOT>`** | 脚本位于 **`bootstrap/scripts/`** 时，用 **`$PSScriptRoot\..\..`** 解析到含 **`bootstrap\pyproject.toml`** 且 **`webhook\pyproject.toml`** 存在的目录；或 **`Resolve-Path`** 从 `-CloneRoot` 参数传入；CI 可用 **`${{ github.workspace }}`** / **`$env:CI_PROJECT_DIR`** 等价绝对路径。 |
| **工作区目录 `$WORKSPACE`** | **首轮运行前目录允许不存在**：执行合同路径 **只能**由 **`bootstrap materialize-workspace --workspace $WORKSPACE`** 创建（Task 7：`workspace_root.mkdir(parents=True, exist_ok=True)`）；闸门脚本 **不得**事先 **`mkdir $WORKSPACE`** 冒充「验收」，也 **不得**要求运维预先建好目录——**创建目录本身是 bootstrap 流程的一环**。须满足 **§3.2**（ASCII、段内无空格）；与克隆根 **互不嵌套**。若目录已残留旧产物：脚本可先 **`Remove-Item -Recurse -Force`** 再 **`materialize-workspace`**，或 **`materialize-workspace ... --force`**（与 Task 7 一致）。**本仓库维护机拟用的生产型示例路径：** **`C:\Cursor WorkSpace\VLA_workplace`** —— 默认不存在；闸门脚本应以 **`-Workspace`** 或 **`$env:VLA_UNATTENDED_WORKSPACE`** 传入（见上文「路径约定」与示例并存说明）。**CI / 无私盘场景**可改用 **`{克隆根}\.cursor_task\bootstrap-unattended-smoke`**（符 `.cursor/rules/workplacestructure.mdc`）。 |
| **工作区 `.env`（步骤 5）** | **`materialize-workspace`** 已写入首份种子 **之后**，再将 **`pipeline-workspace-root.env.example`** **`Copy-Item`** **覆盖** **`{WORKSPACE}\.env`**（**`-Encoding utf8`**）。**刻意覆盖**之目的：使闸门所用 `.env` 与 **仓库提交的样本**完全一致，便于回归对照 **文档样本漂移**；**不是**重复失误。键值为仓库已提交示例即可。**勿**复制 gitignored 的 **`pipeline-workspace-root.env`**（真密钥）。 |
| **junction** | 闸门默认 **`--no-junction-tools`**（最快路径、Linux CI 可跑）；Windows 若要覆盖 junction，可改为脚本可选开关，但 **不作**人机签字等价条件。 |

**须实现的交付物（必选）：**

- **`bootstrap/scripts/run-unattended-acceptance.ps1`**（UTF-8 BOM 或脚本头注释标明编码）：顺序执行（仅用 **`;`** 或分行，**勿** bash `` `&&` ``）；支持 **`-SkipDoctor`**：
  1. **`Set-Location <CLONE_ROOT>`**
  2. **`Push-Location .\bootstrap`** → **`python -m pip install -e ".[test]"`** → **`Pop-Location`**（**BUG-007**；与已实现脚本一致。若已在同一 venv 装过可跳过 —— 可用 **`pip show newvla-production-bootstrap`** 判断）
  3. **`bootstrap install-packages`**
  4. **`bootstrap materialize-workspace --workspace $WORKSPACE --clone-root $CLONE_ROOT --no-junction-tools`** —— **此步创建 `$WORKSPACE` 目录树**（若路径尚不存在）；**勿**在本步之前对 **`$WORKSPACE`** 手动 **`mkdir`**（除非脚本仅为清空残留）。
  5. **`Copy-Item`** `docs\superpowers\samples\pipeline-workspace-root.env.example` → **`$WORKSPACE\.env`**（**覆盖**；理由见上表）。
  6. **若未指定 `-SkipDoctor`：** **`bootstrap doctor --workspace $WORKSPACE`**；任一步失败则 **`exit 1`**。
  7. **若 `-SkipDoctor`：** 跳过步骤 6，步骤 1–5 成功即 **`exit 0`**。
- **`bootstrap/README.md`**：**「落地后无人介入验收」** 小节 — **两档闸门**、上表、与人机签字对照 + **`powershell -File .\bootstrap\scripts\run-unattended-acceptance.ps1`**（CI 示例：`… -SkipDoctor`）。
- **勿**在本 Task 复制 **`interactive-setup`** 内部逻辑；脚本 **仅**调既有 CLI。

**Steps:**

- [ ] **Step 1:** 实现 **`run-unattended-acceptance.ps1`**（含 **`-SkipDoctor`**）；维护者在 **克隆根**：先 **`exit 0`**（带 `-SkipDoctor`），再 **不带** `-SkipDoctor` 在「已装 Cursor/lark」机上验证 **B 档**。
- [ ] **Step 2:** 更新 **`bootstrap/README.md`**（两档闸门、与人机签字边界、CI 与维护机用法）。
- [ ] **Step 3（可选）：** 根目录 **`.github/workflows/`** 或其它 CI：checkout 后 **`powershell -File .\bootstrap\scripts\run-unattended-acceptance.ps1 -SkipDoctor`**（Linux 须 **`--no-junction-tools`**）；失败即红。**勿**向仓库写入真实密钥。
- [ ] **Step 4:** 提交 `feat(bootstrap): unattended acceptance gate script`（README 同行）。

**Gate：** **Merge / CI：** **A 档**（`-SkipDoctor`）**必须绿**。**B 档**（全量 **`doctor`**）在 **维护机**合并前后跑通一次即可记入 Release 备注；**不得**因 CI 无 Cursor 将 PR 判失败。

---

## Self-review（对照 spec）

1. **Spec coverage：** **Task 13 `interactive-setup`** = 与人验收唯一路径；流程 → README + `materialize`；§3.2/§3.4；Tasks 7–11；**Task 12：`ExecutorSettings` + `VLA_WORKSPACE_ROOT` 与工作区 `.env` 一致**；`doctor` + JSON WARNING；文档互链。**Task 14：** **A 档**（`-SkipDoctor`）必绿；**B 档**（全量 **`doctor`**）维护机验证；**不**升格为人机签字替代。**BUG-005 余量：** folder 路由仍可能只消费 JSON；与工作区 `.env` 合同对齐关 BugList，**非**「webhook 读错 `.env` 路径」类 Gap。
2. **Placeholder scan：** 无 TBD；Task 9 实现体在开发时写满 `_check_*` 小函数，禁止留「后续补充」空壳。
3. **Type consistency：** `materialize_workspace(..., link_tools=bool)` 与 CLI `--no-junction-tools` 语义对立统一；`default_clone_root()` 与 `paths.py` 仅一处定义。
4. **与 `2026-04-28-production-bootstrap-deployment-design.md` 一致性：** spec §2.1 / §3.1 已写明 **维护仓库根 `.env` = 种子**、**工作区根 `.env` = 运行合同唯一真源**；materialize 种子顺序与 **`--sync-env-from-clone`** 与 spec §2.1 条 6 对齐；`doctor` 读工作区；JSON 漂移 **WARNING**。本 plan 文首与 spec 对齐。**`env.mdc`：** 已更新；**`AGENTS.md` / `prompts/AGENTS.txt`：** 落地后 renew onboard 句（见 plan 文首）。
5. **本 review 已修计划内问题：** README 示例命令顺序（先 `materialize` 再 `doctor`）；`install_all` 测试补全四包子目录；Task 9 测试与 `run_doctor(workspace=...)` 及 Redis 可选逻辑对齐；doctor 测试改为 patch `_import_markitdown` / `_import_pipeline_packages`。
6. **仍留实现期注意：** 子进程需工作区路径时：**cwd=工作区根** 或 **显式传入与 `--workspace` 相同路径**；`junction` 已存在时靠 **`resolve()` 与目标目录一致** 判定，新建靠 **`mklink` 成功**，不靠 reparse 位掩码。**中等风险已写入正文：** `assert_clone_root_looks_sane`、`--dry-run`/`--force`、Task 12 行号与 pydantic-settings 2.9.x、Task 11 CI≠生产。
7. **验证样本：** `docs/superpowers/samples/pipeline-workspace-root.env*` 与 plan 文前「验证用工作区 `.env` 样本」节；与 **工作区/维护种子** 漂移时记得更新样本（仍 gitignore）。
8. **用户验收：** **仅**承认「`pip install -e .\bootstrap[…]` + `bootstrap interactive-setup`」走通至 `doctor` 退出码可解释；分立子命令分步 **不**单独作为签字路径。**Task 14：** merge **以 A 档**（`-SkipDoctor`）**为闸门**；**B 档** **不得**与人机签字混为一谈（README 须写明）。
9. **落地文档收尾：** **`BugList.md`**（BUG-004/BUG-005 等与「根 `.env` 唯一真源」相关措辞若已与双线 `.env` 演进不符）按事实修订；**`NiceToHave.md`** 总表状态若仓库规则要求与本 plan 同步则更新（见 `.cursor/rules/nice-to-have.mdc`）。

---

## 用户验收主流程（签字用）

> **PowerShell**。**不要**照抄固定盘符；路径须 ASCII、无空格（spec §3.2）。**不要**用 bash 的 `&&` 串联。

```powershell
Set-Location <本机克隆根绝对路径>
python -m pip install -e ".\bootstrap[test]"
bootstrap interactive-setup
```

按终端提示完成：**维护仓库根**（可默认当前目录）、**执行工作区根**、可选预览/无 junction；**编辑工作区 `.env`**；直至 **`doctor` 结束**。随后按需：`feishu-onboard`（同步工作区 `.env`）、设置 **`VLA_WORKSPACE_ROOT`**、起 Redis/webhook（交互结束语须提醒）。

### 人工验收操作路径（展开说明）

与上文「理想交互流程」一致；本节便于甲方/运维对照「做到哪一步算 bootstrap 人机验收闭环」，**不等于**投产起服全流程。

**环境与前提**

- **OS：** Windows；**Shell：** PowerShell（命令链勿用 bash 式 `` `&&` ``；见 `.cursor/rules/ps.mdc`）。
- **克隆根：** 本维护仓库在本机任意目录（占位 `<CLONE_ROOT>`）；路径形状须满足 design spec **§3.2**（典型：**ASCII**、路径段 **无空格**）。
- **Python：** **≥3.12**，与本 plan「单机统一 Python」一致；后续 **`pip install -e`** 装入 **当前使用的同一解释器**（是否带 `[test]`  extras 按仓库/README 约定）。

**签字主路径（步骤顺序）**

1. **`Set-Location <CLONE_ROOT>`**（或等价进入克隆根）。
2. **`python -m pip install -e ".\bootstrap[test]"`**（或与 README 一致的 install 串）。
3. **`bootstrap interactive-setup`**（**唯一**与人验收签字对齐的 CLI 入口；实现见 **Task 13**）。
4. **按终端提示交互输入**（实现细则以交互模块为准），通常包括：
   - **维护仓库根：** 多为当前目录，且须通过 **`assert_clone_root_looks_sane`**；若不成立则改为输入可解析的克隆根绝对路径或使用 **`--clone-root`** 语义（见 **Task 5**）。
   - **执行工作区根：** **必填**、**绝对路径**；须经 **`validate_workspace_root_path`**；与克隆根 **互不嵌套**（**§3.2**）。
   - **可选：** **`--dry-run`** 预览物化、**`--no-junction-tools`**（或等价）等。
5. **程序内部顺序（无需人手敲分立子命令）：** **`install_packages` → `materialize_workspace` →** 界面提示 **用编辑器打开 `{WORKSPACE}\.env`** **→ `run_doctor`**（与 spec **§2.1** 一致）。
6. **人工编辑工作区根 `.env`：** 补齐 **`REDIS_URL`、`FOLDER_ROUTES_FILE`**、飞书/Dify 等运行密钥；**勿**增加 **`PIPELINE_WORKSPACE_PATH`** 等与 **`--workspace` 重复的路径抽象**（见 plan 文首「路径表达」）。
7. 按提示继续（如 **Enter**），直至 **`doctor` 针对该工作区执行完毕**；以 **`doctor` 退出码可解释**（含已知 WARNING，如 JSON 漂移 **BUG-005**）作为 **bootstrap 侧人机验收的可收口判据**。
8. **下列步骤不在同一子进程内强行完成**，但 **交互结束前须 stdout 简短提醒**，交接文档须一致：**按需 `feishu-onboard`**（往往只写维护仓根 `.env`，仍须按 **`bootstrap/README.md` / `onboard/README.md`** **合并或复制进工作区 `.env`**）；**设置进程环境变量 `VLA_WORKSPACE_ROOT`**（与 **`materialize-workspace --workspace`** **同字符串**，供 **Task 12** **`ExecutorSettings`** 加载工作区 `.env`）；**起 Redis、uvicorn/webhook/RQ`**——属 **投产或联调**，甲乙方可在合同中另行约定是否纳入「验收签字」范围。

**刻意不作为签字替代的路径**

- **不**单独以「依次手动执行 **`install-packages` → `materialize-workspace` → `doctor`**」代替 **`interactive-setup`**；该拆法仅对应文末「**分步命令附录**」与 CI/排障。
- **不**指望仅从 **即将加载的** 工作区 `.env` **首次读出** 自身路径来设置 **`VLA_WORKSPACE_ROOT`**（循环依赖）；路径以 **`--workspace` / 交互收集值 / 运维注入 env** 为准。

---

## 分步命令附录（CI / 自动化 / 排障，**非**验收替代路径）

> 下列与 spec §2.1 顺序一致，仅供脚本拆分、失败定位；**人验签字仍以「用户验收主流程」为准。**

```powershell
# 脚本拆分时：先设变量（示例）
$CLONE_ROOT = $env:NEWVLA_CLONE_ROOT
$WORKSPACE  = $env:NEWVLA_WORKSPACE_ROOT
if (-not $CLONE_ROOT -or -not $WORKSPACE) { throw "请先设置 NEWVLA_CLONE_ROOT / NEWVLA_WORKSPACE_ROOT" }
```

1. **目的：确认文档与生产启动约定可读。**

   - 打开并通读：`$CLONE_ROOT\bootstrap\README.md`、`$CLONE_ROOT\webhook\操作手册.md`（生产/bootstrap 相关节）。

2. **目的：进入维护仓库并安装 bootstrap 包。**

```powershell
Set-Location $CLONE_ROOT
python -m pip install -e ".\bootstrap[test]"
```

3. **目的：确认 CLI 子命令存在。**

```powershell
bootstrap --help
bootstrap interactive-setup --help
bootstrap doctor --help
bootstrap install-packages --help
bootstrap materialize-workspace --help
```

（验收主路径以 **`interactive-setup`** 为准；上列分立子命令 **仅**排障/脚本拆分。）

4. **目的：把四子包 + markitdown 装进当前 Python（与 plan 一致）。**

```powershell
bootstrap install-packages
```

5. **目的：首启物化工作区（§3.4 树 + 工作区根 `.env`）；维护仓须有 `.env` 或 `.env.example`。**

```powershell
bootstrap materialize-workspace --workspace $WORKSPACE
```

6. **目的：补齐运行密钥与合同（运行真源 = 工作区根 `.env`）。**

   - 用编辑器打开 `$WORKSPACE\.env`，按需填写 `REDIS_URL`、`FOLDER_ROUTES_FILE`、飞书/Dify 等（勿加 `PIPELINE_WORKSPACE_PATH`）。

7. **目的：自检环境与合同（含 JSON 漂移 WARNING）。**

```powershell
bootstrap doctor --workspace $WORKSPACE
```

8. **目的：生产起 webhook/RQ 前注入工作区路径（与 `--workspace` 同字符串）。**

```powershell
$env:VLA_WORKSPACE_ROOT = $WORKSPACE
```

   - 随后在本会话或 Windows 服务环境变量中启动 `uvicorn` / RQ worker（命令以你现网为准；未设 `VLA_WORKSPACE_ROOT` 时行为为 dev：读克隆根 `.env`，用于对照）。

9. **目的：核对 §3.4 工具联接（仅 Windows 实机）。**

```powershell
Get-Item "$WORKSPACE\tools\dify_upload" | Select-Object LinkType, Target
Get-Item "$WORKSPACE\tools\feishu_fetch" | Select-Object LinkType, Target
```

---

### 附加核验（可选，仍含命令）

| 目的 | 命令示例 |
|------|----------|
| 维护仓改了 `.env`，要**覆盖**工作区 `.env` | `bootstrap materialize-workspace --sync-env-from-clone --workspace $WORKSPACE --clone-root $CLONE_ROOT`（克隆根非默认推导时 `--clone-root` 必填） |
| 再次物化且已有非空 `rules/`，须确认覆盖 | 先无 `--force` 应失败；`bootstrap materialize-workspace --workspace $WORKSPACE --force` 应成功 |
| 仅预览不写盘 | `bootstrap materialize-workspace --workspace $WORKSPACE --dry-run` |
| wheel/非克隆树须指定克隆根 | `bootstrap materialize-workspace --clone-root $CLONE_ROOT --workspace $WORKSPACE` |
| 自动化回归 | `Set-Location $CLONE_ROOT; python -m pytest .\bootstrap\tests -v`；`Set-Location "$CLONE_ROOT\webhook"; python -m pytest .\tests\test_settings.py -v`；Task 14 **A 档：** `powershell -File .\bootstrap\scripts\run-unattended-acceptance.ps1 -SkipDoctor` |
| P0 文案验收 | 对照 `docs\superpowers\specs\2026-04-28-production-bootstrap-deployment-design.md` §7 逐条勾选 |

---
