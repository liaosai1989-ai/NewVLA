# Feishu App Folder Onboard Implementation Plan

> **落地状态：实现已合入（`onboard/`）；清单/签字验收未闭环**（2026-04-28；与正文 §6.2/§7.3 及文首修订说明、`onboard/README.md` 一致。）

## 修订说明

- **2026-04-29（事件驱动 per-doc subscribe；更新 BUG-006 合同）：** `feishu-onboard` **仅**夹级 `folder_token` subscribe；**webhook** 在 **`drive.file.created_in_folder_v1`** 上对 `file_token` 再 tenant subscribe（[design 修订 2026-04-29 首条](../specs/2026-04-26-feishu-app-folder-onboard-design.md)、`webhook_cursor_executor.feishu_drive_subscribe`）。**禁止**夹内历史全量枚举 subscribe；**不**用户 OAuth。下文若仍写「禁止一切 per-doc subscribe」，作废。
- **2026-04-27**：与 [feishu-app-folder-onboard-design v2026-04-27 修订](../specs/2026-04-26-feishu-app-folder-onboard-design.md) 对齐 — `validate_qa_rule_file` 允许 `prompts/rules/...` 与 `rules/...`；`test_validate` / README / 操作手册已同步。下文内嵌代码块中旧版「仅 `rules/`」段以**仓库 `onboard/src/feishu_onboard/validate.py` 现网实现**为准。
- **2026-04-27（飞书侧「权限/可见性」与正文关系；实机/清单验收未闭环）**：仓库内 `onboard` 该段行为已**收束为单路径**——根 `.env` 必配 `FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID` 等，且对新建/既有 `folder_token` 仅调用 `POST .../drive/v1/permissions/.../members?type=folder`（`add_folder_user_collaborator`），**不**再实现 `patch_public` / `PATCH .../public` / metas 分岔。**下文**（含本文件 **Goal / Architecture 首段**、**内嵌代码样例**、**逻辑清单第 7 点原文** 等）**保留为成稿/历史设计**，不逐段改为与现网同字；**与现网差异**以本修订说明、[`onboard/src/feishu_onboard/flow.py`](../../../onboard/src/feishu_onboard/flow.py)、[`onboard/src/feishu_onboard/feishu_client.py`](../../../onboard/src/feishu_onboard/feishu_client.py) 与 [`onboard/README.md`](../../../onboard/README.md) 为准。内嵌 `test_public_ok` 等片段仅作**当时** Task 书写参考；**现网单测**以 `onboard/tests/*.py` 为准。**在验收签字前**勿将本 plan 静态正文当作唯一 SoT。
- **2026-04-27（夹级 subscribe 已合入现网；BUG-006）**：`FeishuOnboardClient.subscribe_folder_file_created` 与 `flow.run_onboard` 在 **`add_folder_user_collaborator` 之前** 调用，契约与 `webhook/scripts/subscribe_byvwf_tds.py` 及 [feishu-app-folder-onboard-design 修订说明·夹级事件 subscribe](../specs/2026-04-26-feishu-app-folder-onboard-design.md) 一致。下文 **Architecture** 中「`tenant_access_token`、建文件夹、公开权限 `PATCH`」为历史成稿；现网为 **建夹 →（阶段 A 写盘）→ 夹级 subscribe → 加协作者 → `lark-cli` → 条件满足时阶段 B**。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在仓库中新增可安装的交互式 `onboard` 工具，按 [2026-04-26-feishu-app-folder-onboard-design.md](../specs/2026-04-26-feishu-app-folder-onboard-design.md) 完成飞书 App 文件夹创建、企业内可见尝试、两阶段根 `.env` 写入与 `lark-cli config init`，并满足续跑/幂等与脱敏要求。

**Architecture:** 在仓库根新增独立 Python 子包 `onboard/`，不并入 `webhook` 运行时。核心拆成无 IO 的纯函数（键名校验、`qa_rule_file` 路径合同、从已解析的 `dict` 校验 `DIFY_TARGET_*` 组）、带 `httpx` 的飞书客户端（`tenant_access_token`、建文件夹、公开权限 `PATCH`）、可单测的 `.env` 行级读写与原子 `os.replace`、子进程封装的 `lark-cli` 初始化。CLI 层做交互、编排两阶段落盘与阶段 B 门禁。不引入与 `dify_upload` 共享的顶层包，允许从环境键约定复制字段列表。

**Tech Stack:** Python 3.12+，`httpx`，`pytest`，`subprocess`；可选开发依赖 `pytest-httpx` 用于 Mock 传输层。

---

## Scope Check

- 本 plan **只**交付 `onboard` 包与单测、README；不强制在同一 PR 内改 `webhook` 去消费根 `.env` 路由（见 [2026-04-26-root-env-and-dify-target-contract-design.md](../specs/2026-04-26-root-env-and-dify-target-contract-design.md) 的 **webhook 侧 plan**；两者可并行，但 `onboard` 写入的键名必须与本 spec §5 一致，便于后续 webhook 接）。
- 第一版**不**强制实现 `webhook/config/folder_routes.example.json` 从 `.env` 导出；若加可选子命令，单独 commit。
- 参考实现：`old_code/mini_package/` 仅作 **API 形状与脚本流程** 参考，**禁止** 把占位 `PlaceholderFeishuAppFolderClient` 拷入新包。
- **与 upstream spec 同步**：[feishu-app-folder-onboard-design.md](../specs/2026-04-26-feishu-app-folder-onboard-design.md) §1 若将「企业内可见」从 P1 提升为 P0 门禁，会牵动 §7.3 与阶段 B 是否可写入索引；**届时须先改 spec / NTH-006 再改本包实现**，本 plan 默认按 P1（权限失败仍保留阶段 A、**不** 写 `FEISHU_FOLDER_ROUTE_KEYS`）执行。
- **与 fetch / `lark-cli` 工作区 spec 同步**（必读）：[2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](../specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 规定凭证由**初始化层** `config init` 写入、**`feishu_fetch` 仅消费已初始化环境**；**执行上下文须一致**（该 spec §6.1、§8.1、§9.2）。本 plan 中 `lark_config_init` / `lark_config_show_verify_app_id` 的**生产** `cwd` 必须为**管线仓根** `repo_root()`（与根 `.env` 真源同目录语义），与后续在该工作区跑抓取时 `lark-cli` 子进程所见的配置**同一套**；详见下文 **「与 feishu-fetch lark-cli spec 的衔接」**。

## 与 feishu-fetch lark-cli spec 的衔接

[2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](../specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 把**执行环境初始化**与 **`feishu_fetch` 预检/抓取** 的边界、**`config show` 输出与 CLI 版本**、**测试分层 L0/L1/L2**（§11.3）写进同一份 spec。本 `onboard` 包在成功路径上承担「初始化层」中对 **`lark-cli` 的 `config init` + 校验**（与 [feishu-app-folder-onboard-design](../specs/2026-04-26-feishu-app-folder-onboard-design.md) 的 lark 门禁一致）。

| 本 plan 落点 | 对 fetch spec 的对应 |
|-------------|----------------------|
| `lark_config_init` / `lark_config_show_verify_app_id` 的 **生产** `cwd` = `repo_root()` | §6.1 执行上下文一致性；避免 init 在 A、抓取在 B 导致假「未初始化」 |
| Task 5 单测用 **mock 子进程**、不强制本机 `lark-cli` | §11.3 **L0** 为默认、必达于默认 `pytest` |
| README 声明 **`lark-cli` 支持的主/次版本**；`config show` 解析与测试样例**锁住**该范围 | §9.2「`config show` 与版本」、§10.4 |
| 真 CLI、真凭证的冒烟 | **L1 可选**（显式门控/单独 job/本地手册），**不** 作为对任意贡献者默认红绿的 PR 必达；§10.3 全量真抓取验收可走 **L2** 与操作手册 |
| 不在本 plan 内改 `feishu_fetch` 源码 | fetch spec 的 `feishu_fetch` 合同与测试由**另 PR / 另 plan** 跟进；本 plan 只保证 **onboard 与「仓根 + `.env`」约定** 与 fetch spec 不冲突 |

**实现硬性约定：** `flow.run_onboard`（及任何生产路径）调用 `lark_config_init` / `lark_config_show_verify_app_id` 时，**第一参数 `cwd` 传 `repo_root()`**，**不得** 用 `tmp_path` 或临时目录作为生产上的 init/show 工作目录。测试中 `tmp_path` 仅用于**隔离**子进程副作用。

## File Structure

```text
c:\Cursor WorkSpace\NewVLA\
├─ .env  （运行时真源；开发可用 .env.example 手动复制，本 plan 不强制新增）
├─ onboard\
│  ├─ pyproject.toml
│  ├─ README.md
│  ├─ src\
│  │  └─ feishu_onboard\
│  │     ├─ __init__.py
│  │     ├─ env_paths.py          # 仓库根、.env 绝对路径
│  │     ├─ env_contract.py        # 键名、Dify 组必需后缀、两阶段要写的键
│  │     ├─ validate.py            # route_key / qa_rule_file / parent_token
│  │     ├─ env_store.py          # 读 .env 为 str->str、行级更新、原子写、去重键
│  │     ├─ feishu_client.py      # 脱敏、HTTP
│  │     ├─ lark_cli.py           # config init + show 解析 appId
│  │     ├─ flow.py                # 续跑/创建、两阶段、错误分支
│  │     └─ cli.py                 # 交互 + argparse
│  └─ tests\
│     ├─ conftest.py
│     ├─ test_env_paths_override.py  （可选）
│     ├─ test_validate.py
│     ├─ test_env_store.py
│     ├─ test_env_contract.py
│     ├─ test_feishu_client.py
│     ├─ test_lark_cli.py
│     └─ test_flow.py
```

设计说明：

- `env_store` 用**逐行**解析以保留注释与未识别行；对「已知要更新的键」做原位替换，否则在文件**末尾**追加新行（YAGNI：不实现复杂分区插入）。
- 两阶段写：`flow.py` 调 `env_store` 两次（阶段 A、阶段 B），两次均走同一原子写函数。
- 飞书限流/错误码：在 `onboard/README.md` 建「参考」表，链接开放平台 **drive v1 create_folder**、**permissions public**、**auth v3 tenant_access_token**，并抄录 `1061045`、`1062507`、`1063003` 等**以官方当时文档为准**的编号（若官方改名则随文档更新，不在代码里写死长说明）。

---

### Task 1: 子包骨架与可执行入口

**TDD 说明：** 自 **Task 2** 起按红绿重构写测例；本 Task 仅为**可安装脚手架**与路径解析，不强制单测。若需 CI 最小编排，可另加 `tests/test_env_paths_override.py`（见 Step 2 后可选段落）。

**Files:**

- Create: `c:\Cursor WorkSpace\NewVLA\onboard\pyproject.toml`
- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\__init__.py`
- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\env_paths.py`
- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\cli.py`（先仅占位 `main`）
- Create: `c:\Cursor WorkSpace\NewVLA\onboard\README.md`（三行：用途、安装、跑 `feishu-onboard --help`）
- Test: 无（可选见 Step 2 末）

- [ ] **Step 1: 编写 `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "feishu-onboard"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27,<0.29",
]
[project.scripts]
feishu-onboard = "feishu_onboard.cli:main"

[project.optional-dependencies]
test = [
  "pytest>=8.3,<9.0",
  "pytest-httpx>=0.30,<0.32",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

实现落地后按仓库 CI 上 **pytest-httpx 实际工作版本** 调整上界；若 `httpx_mock` 装饰器名变更，以该版本文档为准。

- [ ] **Step 2: 编写 `env_paths.py`**

约定：**默认**从包内 `__file__` 推断仓库根（`onboard` 为 editable 且目录结构不变时指向管线仓根）。若包被**非 editable** 安装到 `site-packages`，推断会失效，须设置环境变量 **`FEISHU_ONBOARD_REPO_ROOT`** 为**绝对路径**的管线仓根（实现：`expanduser` + `resolve`），再读根 `.env`。

```python
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    override = (os.environ.get("FEISHU_ONBOARD_REPO_ROOT") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def root_dotenv_path() -> Path:
    return repo_root() / ".env"
```

**Step 2 可选单测**（`tests/test_env_paths_override.py`）：`monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))` 后断言 `root_dotenv_path() == tmp_path / ".env"`。

- [ ] **Step 3: 编写 `__init__.py` 与 `cli.py` 占位**

`__init__.py` 可为空或 `__version__ = "0.1.0"`。

`cli.py`:

```python
from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="feishu-onboard")
    parser.add_argument(
        "--force-new-folder",
        action="store_true",
        help="已有 FEISHU_FOLDER_<KEY>_TOKEN 时仍调用创建文件夹",
    )
    _ = parser.parse_args()
    print("onboard: not implemented")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 可编辑安装**

Run:

```powershell
cd "c:\Cursor WorkSpace\NewVLA\onboard"
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\feishu-onboard.exe --help
```

Expected: 显示 `argparse` 帮助，含 `--force-new-folder`。

- [ ] **Step 5: Commit**

```powershell
cd "c:\Cursor WorkSpace\NewVLA"
git add onboard/pyproject.toml onboard/README.md onboard/src/feishu_onboard/
git commit -m "feat(onboard): bootstrap package and CLI entry"
```

---

### Task 2: 校验纯函数与 Dify 组合同

**Files:**

- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\env_contract.py`
- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\validate.py`
- Test: `c:\Cursor WorkSpace\NewVLA\onboard\tests\test_validate.py`
- Test: `c:\Cursor WorkSpace\NewVLA\onboard\tests\test_env_contract.py`

- [ ] **Step 1: 编写失败用例（先写测试）**

`tests/test_validate.py`:

```python
import pytest

from feishu_onboard.validate import (
    is_safe_env_key,
    validate_dify_target_key,
    validate_parent_folder_token,
    validate_qa_rule_file,
    validate_route_key,
)


def test_route_key_rejects_invalid():
    with pytest.raises(ValueError, match="route_key"):
        validate_route_key("1AB")


def test_route_key_ok_normalizes_case():
    assert validate_route_key("  team_a  ") == "TEAM_A"
    validate_route_key("TEAM_A")


def test_qa_not_under_rules():
    with pytest.raises(ValueError, match="rules"):
        validate_qa_rule_file("other/qa.mdc")
    with pytest.raises(ValueError, match="rules"):
        validate_qa_rule_file("prompts/other/qa.mdc")


def test_qa_dotdot_rejected():
    with pytest.raises(ValueError):
        validate_qa_rule_file("rules/../x.mdc")


def test_qa_ok():
    validate_qa_rule_file("rules/qa/team.mdc")
    validate_qa_rule_file("prompts/rules/qa/folders/folder_rule_template.mdc")


def test_parent_token_empty_ok():
    validate_parent_folder_token("")


def test_parent_token_too_long():
    with pytest.raises(ValueError):
        validate_parent_folder_token("a" * 300)


def test_is_safe_env_key():
    assert is_safe_env_key("TEAM_A1")
    assert not is_safe_env_key("1AB")


def test_dify_target_key_rejects_invalid():
    with pytest.raises(ValueError, match="dify_target_key"):
        validate_dify_target_key("1AB")


def test_dify_target_key_ok_normalizes_case():
    assert validate_dify_target_key("  team_a  ") == "TEAM_A"
    assert validate_dify_target_key("TEAM_A") == "TEAM_A"
```

`pytest.raises(..., match="route_key"|"dify_target_key")` 依赖错误信息中含该英文词；若将来消息全中文化，须同步改 `match` 或改用 `pytest.raises(ValueError)` + 自定义检查。

`vla_env_contract/tests/test_env_contract.py`（合同测试；**`dify_group_present`** 仍在 **`feishu_onboard.validate`**）:

```python
from feishu_onboard.validate import dify_group_present
from vla_env_contract import dify_group_keys, required_dify_group_suffixes


def test_dify_group_complete():
    env = {
        "DIFY_TARGET_X_API_BASE": "https://a/v1",
        "DIFY_TARGET_X_API_KEY": "k",
        "DIFY_TARGET_X_HTTP_VERIFY": "true",
        "DIFY_TARGET_X_TIMEOUT_SECONDS": "10",
    }
    dify_group_present(env, "X")
    for suf in required_dify_group_suffixes():
        assert f"DIFY_TARGET_X_{suf}" in dify_group_keys("X")


def test_dify_group_missing_key_raises():
    env = {"DIFY_TARGET_X_API_BASE": "https://a/v1"}
    with pytest.raises(ValueError, match="DIFY_TARGET_X_API_KEY|缺少"):
        dify_group_present(env, "X")


def test_dify_group_empty_value_raises():
    env = {
        "DIFY_TARGET_X_API_BASE": "https://a/v1",
        "DIFY_TARGET_X_API_KEY": "",
        "DIFY_TARGET_X_HTTP_VERIFY": "true",
        "DIFY_TARGET_X_TIMEOUT_SECONDS": "10",
    }
    with pytest.raises(ValueError):
        dify_group_present(env, "X")
```

**业务侧「冲突」不在本 Task 测**（见 Task 6「冲突与唯一性」）；此处只保证**格式**与 **Dify 组非空**。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd "c:\Cursor WorkSpace\NewVLA\onboard"
.\.venv\Scripts\python.exe -m pip install -e .[test]
.\.venv\Scripts\python.exe -m pytest tests\test_validate.py tests\test_env_contract.py -v
```

Expected: 大量 `ImportError` / 失败，直到实现完成。

- [ ] **Step 3: 实现 `env_contract.py`**

```python
from __future__ import annotations

# 与 spec §5.4 中 Dify 组一致
def required_dify_group_suffixes() -> tuple[str, ...]:
    return ("API_BASE", "API_KEY", "HTTP_VERIFY", "TIMEOUT_SECONDS")


def dify_group_keys(dify_target_key: str) -> list[str]:
    k = dify_target_key.strip().upper()
    return [f"DIFY_TARGET_{k}_{s}" for s in required_dify_group_suffixes()]


def feishu_folder_group_keys(route_key: str) -> list[str]:
    r = route_key.strip().upper()
    return [
        f"FEISHU_FOLDER_{r}_NAME",
        f"FEISHU_FOLDER_{r}_TOKEN",
        f"FEISHU_FOLDER_{r}_DIFY_TARGET_KEY",
        f"FEISHU_FOLDER_{r}_DATASET_ID",
        f"FEISHU_FOLDER_{r}_QA_RULE_FILE",
    ]


def route_keys_list_key() -> str:
    return "FEISHU_FOLDER_ROUTE_KEYS"
```

- [ ] **Step 4: 实现 `validate.py`**

```python
from __future__ import annotations

import re
from pathlib import Path

_RE_ENV_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
_MAX_TOKEN_LEN = 256


def is_safe_env_key(name: str) -> bool:
    return bool(_RE_ENV_KEY.match(name.strip()))


def validate_route_key(route_key: str) -> str:
    s = route_key.strip().upper()
    if not is_safe_env_key(s):
        raise ValueError("route_key 必须匹配 ^[A-Z][A-Z0-9_]*$")
    return s


def validate_dify_target_key(dify_target_key: str) -> str:
    s = dify_target_key.strip().upper()
    if not is_safe_env_key(s):
        raise ValueError("dify_target_key 必须匹配 ^[A-Z][A-Z0-9_]*$")
    return s


def validate_qa_rule_file(relative: str) -> str:
    p = relative.strip().replace("\\", "/")
    if p.startswith("/") or Path(p).is_absolute():
        raise ValueError("qa_rule_file 禁止绝对路径")
    parts = [x for x in p.split("/") if x != ""]
    if ".." in parts:
        raise ValueError("qa_rule_file 禁止 ..")
    if not parts:
        raise ValueError("qa_rule_file 不能为空")
    under_rules = parts[0] == "rules"
    under_prompts_rules = len(parts) >= 2 and parts[0] == "prompts" and parts[1] == "rules"
    if not (under_rules or under_prompts_rules):
        raise ValueError(
            "qa_rule_file 必须为 rules/ 或 prompts/rules/ 下相对路径，禁止 .."
        )
    return p


def validate_parent_folder_token(token: str) -> str:
    t = token.strip()
    if len(t) > _MAX_TOKEN_LEN:
        raise ValueError("parent_folder_token 过长")
    if not t:
        return ""
    for ch in t:
        if ch in "\r\n\x00":
            raise ValueError("parent_folder_token 含非法字符")
    return t


def dify_group_present(env: dict[str, str], dify_target_key: str) -> None:
    from .env_contract import dify_group_keys

    for key in dify_group_keys(dify_target_key):
        v = (env.get(key) or "").strip()
        if not v:
            raise ValueError(
                f"根 .env 缺少完整 Dify 组: 缺少非空 {key}（dify_target_key={dify_target_key}）"
            )
```

- [ ] **Step 5: 运行测试通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_validate.py tests\test_env_contract.py -v`

Expected: 全部 **PASSED**。

- [ ] **Step 6: Commit**

```powershell
git add onboard/src/feishu_onboard/env_contract.py onboard/src/feishu_onboard/validate.py onboard/tests/
git commit -m "feat(onboard): validate route keys, qa_rule_file, Dify group"
```

---

### Task 3: `.env` 行级读入、更新与原子写

**Files:**

- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\env_store.py`
- Test: `c:\Cursor WorkSpace\NewVLA\onboard\tests\test_env_store.py`

- [ ] **Step 1: 写失败测试**

`tests/test_env_store.py`（核心用例，完整可运行）:

```python
from pathlib import Path

from feishu_onboard import env_store


def test_load_parse_roundtrip_preserves_comment(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("# keep\nFOO=1\n", encoding="utf-8")
    m = env_store.load_flat_map(p)
    assert m["FOO"] == "1"
    env_store.set_keys_atomic(p, {"FOO": "2"}, create_backup=False)
    text = p.read_text(encoding="utf-8")
    assert "# keep" in text
    assert "FOO=2" in text


def test_set_dedup_same_key(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("A=1\nA=2\n", encoding="utf-8")
    env_store.set_keys_atomic(p, {"A": "3"}, create_backup=False)
    assert p.read_text(encoding="utf-8").count("A=") == 1
    m = env_store.load_flat_map(p)
    assert m["A"] == "3"


def test_load_duplicate_key_last_line_wins(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("A=1\nA=2\n", encoding="utf-8")
    assert env_store.load_flat_map(p)["A"] == "2"
```

- [ ] **Step 2: 实现 `env_store.py`**

行为要求：UTF-8；与目标 `.env` 同目录写临时文件 `os.replace`；临时文件 Unix `0o600`；Windows 用 `open(..., opener=_win_restrict)` 或等效，若做不到文档说明降级策略。**Windows 与 §6.3：** `os.chmod` 与 ACL 与 Unix 不完全等价；`onboard/README.md` 须写明「尽量用户独占；以当前 OS 实际行为为准」。

提供：

- `load_flat_map(path) -> dict[str, str]`：自上而下扫描；**同一键多行时取最后一次出现**（最后一行会覆盖之前解析到的值，**空值也会覆盖**）。与 `set_keys_atomic` 去重后再读的行为一致。见上 `test_load_duplicate_key_last_line_wins`。
- `set_keys_atomic(path, mapping, *, create_backup: bool)`：更新或追加键；`create_backup` 为 True 时复制一份 `.env.bak` 同目录（仅用于调试，默认可 `False`）。


**`load` / `set` 契约（实现后自检）**


| 操作 | 行为 |
|------|------|
| `load_flat_map` | 重复键：最后一行值；不存在文件 → `{}` |
| `set_keys_atomic` 后同键 | 仅保留**首次出现行**上的更新值、删除后续重复行 |
| 与 spec §6.3 | 每阶段各一次 `set` + 同目录 `os.replace` 原子化 |

实现提示（给工程师的完整核心逻辑，可直接粘贴后微调）:

```python
from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path


def load_flat_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    # 自顶向下：后出现的键覆盖先出现的
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        out[k] = v.strip()
    return out


def set_keys_atomic(path: Path, updates: dict[str, str], *, create_backup: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if create_backup and path.is_file():
        path.with_suffix(path.suffix + ".bak").write_bytes(path.read_bytes())

    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines and not path.is_file():
        lines = []

    def norm_line(line: str) -> tuple[str | None, str | None]:
        raw = line
        t = line.lstrip()
        if not t or t.lstrip().startswith("#"):
            return None, raw
        if "=" not in t:
            return None, raw
        k, v = t.split("=", 1)
        return k.strip(), raw

    for k, v in updates.items():
        new_line = f"{k}={v}\n"
        idxs: list[int] = []
        for i, line in enumerate(lines):
            k2, _ = norm_line(line)
            if k2 == k:
                idxs.append(i)
        if idxs:
            first = idxs[0]
            lines[first] = new_line
            for i in reversed(idxs[1:]):
                del lines[i]
        else:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(new_line)

    dir_ = path.parent
    fd, tmp = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=dir_)
    try:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines if lines else [""])
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
```

- [ ] **Step 3: 运行测试**

`pytest tests\test_env_store.py -v` → 全部 **PASSED**。

- [ ] **Step 4: Commit**

```powershell
git add onboard/src/feishu_onboard/env_store.py onboard/tests/test_env_store.py
git commit -m "feat(onboard): atomic .env read/write with comment preservation"
```

---

### Task 4: 飞书 HTTP 客户端（脱敏 + 三接口）

**Files:**

- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\feishu_client.py`
- Test: `c:\Cursor WorkSpace\NewVLA\onboard\tests\test_feishu_client.py`

合同（以官方为准，若路径变更只改本模块常量与 README）:

- `POST` `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`，body: `app_id`, `app_secret`。
- `POST` `https://open.feishu.cn/open-apis/drive/v1/files/create_folder`，`Authorization: Bearer`。
- `PATCH` `.../open-apis/drive/v1/permissions/{token}/public?type=...`（`type` 对文件夹按文档选，常见为 `file`；错误则 §7.3）。

- [ ] **Step 1: 用 `pytest-httpx` 写三测例**

`tests/test_feishu_client.py`:

```python
import json

import httpx
import pytest

from feishu_onboard.feishu_client import FeishuOnboardClient, fetch_tenant_access_token


@pytest.mark.httpx_mock
def test_tenant_token(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"code": 0, "tenant_access_token": "t0", "expire": 3600},
    )
    t = fetch_tenant_access_token("id", "sec")
    assert t == "t0"


@pytest.mark.httpx_mock
def test_create_folder(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://open.feishu.cn/open-apis/drive/v1/files/create_folder",
        json={
            "code": 0,
            "data": {"token": "fldx", "url": "https://x"},
        },
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    r = c.create_folder("n", parent_folder_token="")
    assert r["folder_token"] == "fldx"
    assert "url" in r


@pytest.mark.httpx_mock
def test_public_ok(httpx_mock) -> None:
    httpx_mock.add_response(
        method="PATCH",
        url=httpx.URL(
            "https://open.feishu.cn/open-apis/drive/v1/permissions/fldx/public",
            params={"type": "file"},
        ),
        json={"code": 0, "data": {}},
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    assert c.patch_public_tenant_readable("fldx", resource_type="file")


@pytest.mark.httpx_mock
def test_create_folder_with_parent_token(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://open.feishu.cn/open-apis/drive/v1/files/create_folder",
        json={"code": 0, "data": {"token": "cfld", "url": "https://p"}},
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    r = c.create_folder("child", parent_folder_token="fld999")
    assert r["folder_token"] == "cfld"
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    body = json.loads(req.content.decode("utf-8"))
    assert body.get("name") == "child"
    assert body.get("folder_token") == "fld999"
```

（若 `create_folder` 的 JSON 字段名以开放平台为准为 `name` + 父级 token 字段名，与上不一致则改断言；实现应将请求体**集中**在一处，便于对官方文档。）

`import json` 置于文件首。

`httpx_mock` 的类型注解与 `@pytest.mark.httpx_mock` 以 `pytest-httpx` 已安装版本文档为准；若装饰器名不同，改为该版本等价写法。`get_requests()` 方法名以所装版本为准（或改用捕获 `request` 的 callback）。

- [ ] **Step 2: 实现并保证 stdout 不打印 body 中 secret**

`feishu_client.py` 对非 `code==0` 只抛 `FeishuApiError`（模块内 `class FeishuApiError(Exception)`），`str()` 用固定中文 + `code` + `msg` 字段，**不** 附加整段 `response.text`。**不** 将完整 URL（含可能出现在 query 的敏感项）与完整 response 默认打到 `logging`/`print`；排障时仅记 operation 名 + `code` + 业务 `msg`。

- [ ] **Step 3: `pytest` 全绿后 commit**

```powershell
git add onboard/src/feishu_onboard/feishu_client.py onboard/tests/test_feishu_client.py
git commit -m "feat(onboard): Feishu token, create_folder, public permission client"
```

---

### Task 5: `lark-cli` 子进程

**Files:**

- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\lark_cli.py`
- Test: `c:\Cursor WorkSpace\NewVLA\onboard\tests\test_lark_cli.py`

- [ ] **Step 1: 写失败测试**（`unittest.mock.patch` 伪造 `subprocess.run` / `subprocess.Popen`，不依赖本机 `lark-cli`）

`tests/test_lark_cli.py`:

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from feishu_onboard.lark_cli import lark_config_init, lark_config_show_verify_app_id


@patch("feishu_onboard.lark_cli.subprocess.run")
def test_config_init_sends_secret_on_stdin_not_argv(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
    lark_config_init(
        tmp_path, "cli_abc", "secret123", lark_command="lark-cli"
    )
    call_kw = mock_run.call_args.kwargs
    assert call_kw.get("input") == "secret123" or (call_kw.get("stdin") is not None)
    argv = mock_run.call_args[0][0]
    assert "secret123" not in " ".join(argv)
    assert "--app-id" in argv or "config" in argv


@patch("feishu_onboard.lark_cli.subprocess.run")
def test_config_show_parses_app_id(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=b'{"appId":"cli_abc"}\n',
        stderr=b"",
    )
    lark_config_show_verify_app_id(Path("."), "cli_abc", lark_command="lark-cli")


@patch("feishu_onboard.lark_cli.subprocess.run")
def test_config_show_mismatch_raises(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=b'{"appId":"other"}\n',
        stderr=b"",
    )
    with pytest.raises(ValueError, match="appId|一致"):
        lark_config_show_verify_app_id(Path("."), "cli_abc", lark_command="lark-cli")
```

实现时若 API 为 `input=` 或 `communicate` 与上不同，以实际封装为准，但**必须**在测试中断言 `app_secret` 未出现在 `argv`。

- [ ] **Step 2: 实现 `lark_cli.py`**

- `lark_config_init(cwd, app_id, app_secret, *, lark_command: str = "lark-cli")`：对 `lark_command config init --app-id <id> --app-secret-stdin` 使用 `subprocess.run(..., input=app_secret.encode("utf-8"), cwd=cwd, check=False, capture_output=True)`（或等效），**不可** 将 `app_secret` 拼入 `args`。**生产**调用时 `cwd` **必须** 为 `repo_root()`，与 [fetch lark-cli spec §6.1/§8.1](../specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 一致。
- `lark_config_show_verify_app_id(cwd, expected_app_id, *, lark_command)`：运行 `lark config show`（或计划 README 中写死的校验子命令，须与 fetch spec §9.2 第一版检查入口一致），从 **stdout 的安全子集** 用 `json` 或正则仅提取 `appId`（大小写以真实输出为准），与 `expected_app_id` 比较；**不匹配**则 `raise ValueError(中文短句)`。 **`cwd` 规则同上**；解析行为须在 README 与**钉死**的 `lark-cli` 版本上可复现，见 fetch spec §9.2「`config show` 与版本」。

**安全：** 默认**不** 将 `stdout`/`stderr` 全文写入日志。失败时只提示「`lark` 子进程失败、退出码=…」+ 可公开的简短片段；`stderr` 可能含环境噪声，**禁止** 假定可原样回显。若 `show` 在某种版本会打印 `app_secret`（以官方为准），**不得** 依赖该子命令的完整转储，须换用不含 secret 的校验路径或仅解析不含敏感字段的 JSON 子集；找不到安全解析则 **lark_ok=false**，走 §7.4（与 `flow` 配合）。

- [ ] **Step 3: `pytest` 全绿后 commit**

```powershell
git add onboard/src/feishu_onboard/lark_cli.py onboard/tests/test_lark_cli.py
git commit -m "feat(onboard): lark-cli config init via stdin and show parse"
```

---

### Task 6: 编排 `flow.py`：续跑、两阶段、分支 §7.3 / §7.4

**Files:**

- Create: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\flow.py`（可含 `OnboardInput` / `OnboardResult` 于同文件或 `models.py` — YAGNI 时同文件即可）
- Test: `c:\Cursor WorkSpace\NewVLA\onboard\tests\test_flow.py`（`tmp_path` 放 `.env`、mock `httpx` / `lark`）

**`OnboardResult`（供实现与 `test_flow` 断言）** — 草图，字段可增减，但须在测试中写出：

```python
from dataclasses import dataclass


@dataclass
class OnboardResult:
    exit_ok: bool
    partial: bool
    public_ok: bool
    lark_ok: bool
    stage_b_index_written: bool
    folder_token: str | None
    folder_url: str | None
```

`partial` 为 True 当且仅当符合 §7.3 或 §7.4 部分完成态；`exit_ok` 为 True 当且仅当阶段 B 已写入且飞书+映射一致（**或** 按 spec 定义的「成功」主路径；与 Task 7 退出码对齐）。

**冲突与唯一性（spec §6.1 / §7.2 / §7.5，业务规则放 `flow` 或 `validate_routes` 小函数，不在 Task 2 的格式校验里）**

从 `load_flat_map(root_dotenv_path())` 得 `m: dict[str,str]`。

1. **`route_key` 与已有分组冲突**（spec §6.1「不与已有 route 冲突」、§7.2）
   - 设 `K = route_key` 大写。若已存在 `FEISHU_FOLDER_{K}_TOKEN`（非空）且本次为**新建**（非续跑/非仅补索引）：
     - 比较已有分组与本次**拟写入**的 `DIFY_TARGET_KEY`、`DATASET_ID`、`QA_RULE_FILE`（与 spec 中 Name 是否参与一致 — 第一版仅比较**业务绑定三字段** + token 是否一致；**不一致**则 **fail**，消息「route 已存在且与本次输入冲突」。
   - 若三字段+token 与已有完全一致，视为**续跑**（不重复建文件夹、不重复写冲突），允许仅补 public / lark / 阶段 B。

2. **`folder_token` 全库唯一**（§7.5、§7.2 已存在其他 route 使用同一 token）
   - 枚举：解析 `m.get("FEISHU_FOLDER_ROUTE_KEYS","")` 为逗号分隔大写 key 列表 `R1,R2,…`；**并**同时扫描**所有**形如 `FEISHU_FOLDER_*_TOKEN` 的键（防「双轨」仅有分组未入索引），对每个 key `rk` 取 `tok = m.get("FEISHU_FOLDER_{rk}_TOKEN")` 非空者。
   - 若某 `rk != K` 且 `tok == 待写入/已持有的 folder_token`，则 **fail**（与另一 route 复用同 token），除非为同一 route 的续跑。

3. **仅补 `FEISHU_FOLDER_ROUTE_KEYS`（续跑、§6.1b）**  
   若分组已全、public_ok 与 lark_ok 在**此前一次运行**中已可判定成功（本 run 中可重试并再次验证），**仅**缺索引：允许只执行阶段 B；测试须覆盖此分支。

**续跑/幂等与 §6.1b 对照表**（`test_flow` 须每行至少 1 个用例 或 注明合并）


| 场景 | 是否调 create | 是否阶段 A | public | lark | 阶段 B |
|------|---------------|------------|--------|------|--------|
| 新 route、全成功 | 是 | 是 | 成功 | 成功 | 是（P1 下） |
| 新 route、仅 public 失 | 是 | 是 | 否 | 仍按 §6.3 尝试 lark | 否 |
| 新 route、lark 失 | 是 | 是 | 是/否 | 否 | 否 |
| 已 token、续跑补 B | 否 | 否/补丁 | 已判 | 已判 | 是 |
| `--force-new-folder` 且已有 token | 是 | 见 spec 警告/孤儿 | … | … | … |

（「P1」= 权限失败不挡阶段 A 但挡 B，与 spec §1 一致。）

逻辑清单（**必须**全部在代码中体现）:

1. 读 `root_dotenv_path()`，若无 `FEISHU_APP_ID` 或 `FEISHU_APP_SECRET` → 失败不写字段（见 spec §7.2）。
2. 解析输入（测试直接传 `OnboardInput` dataclass，CLI 在下一 Task 再灌）。
3. 校验 `dify_group_present` + `validate_qa_rule_file` + `Path(repo_root() / qa_rule_file).is_file()`（`qa_rule_file` 允许 `rules/...` 或 `prompts/rules/...`，见 spec §5.3 修订）。
4. 执行**冲突与唯一性**（上节 1、2）后再分岔。
5. 检查 `FEISHU_FOLDER_<R>_TOKEN`：若已存在且非 `--force-new-folder`，**不** 调 `create_folder`，仅允许「续跑」分支：补公开权限、补 `lark`、在条件允许时补阶段 B（§6.1b 最小集见上表）。
6. 创建文件夹成功 → 阶段 A 写 5 个 `FEISHU_FOLDER_*` + 不碰 `FEISHU_FOLDER_ROUTE_KEYS`。
7. 尝试 `patch_public`；成功记 `public_ok`。
8. 调 `lark_config_init` + `lark_config_show_verify_app_id`（**两调用** 的 `cwd` 均传 **`repo_root()`**，**不得** 用临时目录作生产 init/show）；成功记 `lark_ok`。
9. 仅当 `public_ok and lark_ok` 执行阶段 B：把 `route_key` 追加入 `FEISHU_FOLDER_ROUTE_KEYS`（去重、逗号分隔、大写）。
10. 若 `public_ok` 假：打印 **权限初始化未完成** + `folder_token` + `url` + 补救说明；**不** 执行阶段 B。
11. 若 `lark_ok` 假：同 spec §7.4；**不** 执行阶段 B。

`test_flow.py` **至少** 5 个用例：全成功含阶段 B；仅 public 失有 A 无 B；仅 lark 失有 A 无 B；**两 route 争用同一 `folder_token` 时失败**；**同 route 续跑只补 B**（或补 public + lark 之一）。`mock` 飞书与 `lark` 时不得向断言外泄 secret。

- [ ] **Step 1: 红测 → 实现 → 绿测 → commit** `feat(onboard): orchestrate two-phase env write and gating`

---

### Task 7: 交互式 CLI 与实机验收接口

**Files:**

- Modify: `c:\Cursor WorkSpace\NewVLA\onboard\src\feishu_onboard\cli.py`

- [ ] **Step 1: 使用 `input()` 依次询问** `route_key`, `folder_name`, `dify_target_key`, `dataset_id`, `qa_rule_file`, `parent_folder_token`（空回车 = 空串）。

- [ ] **Step 2: 调 `flow.run_onboard(...)`**；失败 `sys.exit(2)`，部分成功用退出码 `3`（与常见「仅 0/1」脚本不同，**本工具自定义**：0=全成功、2=参数/校验/硬失败、3=部分完成/§7.3/§7.4、1=未预期错误）— **在 README 用表格写清**；若 CI/父进程只认 0/1，集成方用包装脚本将 2/3 映射为需要的行为。

- [ ] **Step 3: Commit** `feat(onboard): interactive CLI for folder onboard`

---

### Task 8: README 与运营说明

**Files:**

- Modify: `c:\Cursor WorkSpace\NewVLA\onboard\README.md`

- [ ] **Step 1: 必含小节**

  - 前置：`qa_rule_file` 指向的 `rules/...` 或 `prompts/rules/...` 文件在**管线仓根**下已存在、根 `.env` 已有 Dify 静态组、`lark-cli` 安装与 `--app-secret-stdin`；`FEISHU_ONBOARD_REPO_ROOT` 非 editable 安装时的说明；退出码 0/1/2/3 表。维护仓可直接使用 `prompts/rules/` 模板，不必为入轨再复制到 `rules/`（与 spec 修订、操作手册一致）。
  - 限流/错误码外链到开放平台 + 本仓库 spec §6.2。
  - 脱敏：不将 `FEISHU_APP_SECRET`、`tenant_access_token`、Dify `API_KEY`、完整 HTTP/子进程序列贴到**未受控** stdout/日志；`folder_token` / URL 在**交互本机终端**可全量展示，对录屏/CI 的掩码见 spec §7.1。
  - 子进程：`lark-cli` 失败时只记录**退出码**与**可公开**的短 err 摘要，**不** 假设 stderr 可全文安全回显（见 Task 5）。
  - **与 fetch spec 一致**：在**管线仓根**（与 `env_paths.repo_root()` 一致）执行 `config init` / `config show` 校验；若 Agent 在**同一工作区根** 跑 `feishu_fetch`，与 [fetch lark-cli spec §6.1](../specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 的「执行上下文一致」同义。声明支持的 **`lark-cli` 主/次版本**（及安装方式），与 Task 5 解析器一致。
  - **测试**：本包默认 `pytest` 为 fetch spec **§11.3 L0**；真 CLI 冒烟为 **L1 可选**（不写入「默认 PR 必跑真云」的硬性条）。

- [ ] **Step 2: Commit** `docs(onboard): README for operators`

---

## Self-Review（对照 spec）

1. **Spec coverage 核对**
   - §5 `.env` 键名、两阶段、索引门禁 → Task 2、6、7。
   - §6.1 输入与校验、§6.1b 续跑 → Task 2、6、7（`qa_rule_file` 含 `prompts/rules/`，见 spec 修订、validate.py 现网）。
   - §6.2 飞书 API → Task 4 + README。
   - §6.3 原子写、阶段 A/B → Task 3、6。
   - §6.4 lark-cli → Task 5、6。
   - §7 脱敏与部分完成态 → Task 4、6、8。
   - §9 验收 → 以 Task 4–7 的集成与 `pytest` 为准；真网验收由操作者在有凭证的环境执行 `feishu-onboard`。
   - **[fetch lark-cli 工作区 spec](../specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md)**：初始化与后续抓取 **同仓根 / 同 `cwd` 语境**（上文「衔接」+ Task 5/6/8）；**L0** = Task 5 mock + 全包默认 `pytest`；**L1/L2** 不强制进默认 PR，与 spec §11.3 一致。`feishu_fetch` 与预检的代码改动**不在**本 plan 范围。

2. **开放点（以官方/落地为准，非空占位）** — 飞书 `PATCH .../public` 的 `type` 枚举、`create_folder` 请求体字段名、错误码表以 [开放平台](https://open.feishu.cn) 与实现时**钉死**的常量为准；`README` 给链接，代码中集中命名，避免三处各写各的。

3. **类型/命名一致性** — `FEISHU_FOLDER_{ROUTE_KEY}_*`，`DIFY_TARGET_{DIFY_KEY}_*`，`FEISHU_FOLDER_ROUTE_KEYS` 全篇一致。

4. **验收表述** — `dify_group_present` 只验证键**非空**；spec §9「静态组**真实存在**」在操作者填真值的前提下由人工/环境保证；本 plan 不另加「ping Dify 连接」必达项（YAGNI）。

## Execution Handoff

Plan 已保存到 `c:\Cursor WorkSpace\NewVLA\docs\superpowers\plans\2026-04-27-feishu-app-folder-onboard-implementation-plan.md`。

**两种执行方式：**

1. **Subagent-Driven（推荐）** — 每 Task 开新子代理，任务间人工快速审查，适合严格 TDD 节奏。  
2. **Inline Execution** — 本会话用 executing-plans 按 Task 批跑并设检查点。

**请指定采用哪一种。**

未装 `pytest-httpx` 时，可对 HTTP 用例加 `skip` 或改用 `httpx.MockTransport`；`feishu_client` 中 `httpx.Client` 须可注入以便测试。
