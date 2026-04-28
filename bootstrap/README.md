# Production Bootstrap（执行工作区物化）

## 用户验收唯一路径（签字）

与 `docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md` §7 一致：**不得**用分立子命令替代本条作为主签字路径。

1. `Set-Location <CLONE_ROOT>`（维护仓库克隆根）。
2. `py -3.12 -m pip install -e ".\bootstrap[test]"`（本仓库 **`requires-python >=3.12`**；未装 `py` 时用 **Python 3.12** 的 `python.exe` 全路径）。**克隆路径某段含空格**且本条报 **`No such file or directory`**、错误路径像 **`...\父级\onboard`**（少仓库名一级）：改 **`Set-Location .\bootstrap`** → **`py -3.12 -m pip install -e ".[test]"`** → **`Set-Location ..`**（根因见 `BugList.md` **BUG-007**；`install-packages` / 闸门脚本已用等价安全调用）。
3. `py -3.12 -m bootstrap interactive-setup`（编排：`install-packages` → `materialize-workspace` → 提示编辑 **`{WORKSPACE}\.env`** → `doctor`）。

运行合同 **`.env` 只在「执行工作区根」**；物理路径 **仅**由交互/`--workspace` 表达。**勿**在工作区 `.env` 增加 `PIPELINE_WORKSPACE_PATH` 等与 CLI 重复的路径抽象。

对立子命令 `doctor`、`install-packages`、`materialize-workspace`：**仅** CI、脚本与排障；**不得**与人验收签字并列为主流程。

### PowerShell（勿用 bash `` `&&` ``）

```powershell
Set-Location <CLONE_ROOT>
py -3.12 -m pip install -e ".\bootstrap[test]"
py -3.12 -m bootstrap interactive-setup
```

物化后按提示用编辑器打开工作区 `.env` 填入密钥；再继续直至 `doctor` 结束。

---

## 路径约定（§3.2）

- **Python 版本**：维护仓根 `.python-version` 标明 **3.12**（供 pyenv 等识别）；与本包 `requires-python` 一致。
- **克隆根**：本仓库在本机的任意目录；路径 **ASCII**、段内 **无空格**；须能通过 `assert_clone_root_looks_sane`（存在 `webhook/pyproject.toml` 与 `bootstrap/pyproject.toml`）。
- **执行工作区根**：运维自选绝对路径，与 **`materialize-workspace --workspace`**、进程环境变量 **`VLA_WORKSPACE_ROOT`** **同一字符串**（见下文 webhook）。
- **互不嵌套**：工作区不得落在克隆根之下（反之亦然）；校验见 `bootstrap/workspace_path.py`。

---

## `--clone-root`

默认从 **editable** 安装的包路径推导克隆根；wheel/仅 site-packages 安装时必须 **`--clone-root <克隆绝对路径>`**。

---

## 一页交接清单（运维）

| 检查项 | 说明 |
|--------|------|
| 工作区 `.env` | **唯一运行合同真源**；与 `--workspace` / `VLA_WORKSPACE_ROOT` 同目录 |
| onboard | `feishu-onboard` 默认写 **维护仓根** `.env`；须 **合并或复制** 进工作区 `.env` |
| BUG-005（遗留 JSON 模式） | 若 **未**配置 `FEISHU_FOLDER_ROUTE_KEYS`、仍走 `FOLDER_ROUTES_FILE` JSON：JSON 内 `pipeline_workspace.path` 须与 **`materialize-workspace --workspace`** / **`VLA_WORKSPACE_ROOT`** 规范化路径一致——见 task-context spec §7、[`pipeline-workspace-root.env.example`](../docs/superpowers/samples/pipeline-workspace-root.env.example)。已配置 `.env` 路由时真源为工作区 `.env`，不以 JSON 双写为主 |
| BUG-007（Windows / `pip` / 路径含空格） | **`install-packages`** 对各子包 **`cwd` + `-e .`**；**`run-unattended-acceptance.ps1`** 在 **`bootstrap` 目录内** 首装。人手在克隆根首装仍遇 **`file:../onboard`** 错位时按上文第 2 步括号说明；排障与复现命令见 `BugList.md` |
| BUG-004 | 见 `BugList.md`；`doctor` 末尾 stderr 提示 |

---

## `feishu-onboard` 与工作区

`FEISHU_ONBOARD_REPO_ROOT`（见 `onboard/README.md`）控制 onboard 写入 **维护仓根**；**不**替代在工作区根 `.env` 中的运行合同。

---

## 物化安全

| 场景 | 命令要点 |
|------|----------|
| 已有非空 `rules/` | 须 **`--force`**（或先备份） |
| 维护仓 `.env` → 覆盖工作区 | **`--sync-env-from-clone`** |
| 仅预览不写盘 | **`--dry-run`**（不满足「产物已落盘」验收） |

---

## 生产启动 webhook / RQ（Task 12）

进程环境 **`VLA_WORKSPACE_ROOT=<与工作区根相同绝对路径>`**，使 **`ExecutorSettings`** 加载 **`{WORKSPACE}/.env`**。  
未设置时 webhook 仍读 **克隆根** `.env`（本地 dev 对照）。

---

## 落地后无人介入验收（闸门）

**不替代人机签字。** Merge/CI 最低门槛为 **A 档**（`-SkipDoctor`）；维护机在完整依赖下再跑 **B 档**（含 `doctor`）。闸门脚本对 **`materialize-workspace` 带 `--force`**，同一 **`Workspace`** 重复跑不会因残留 **`rules/`** 失败。

| 档位 | 内容 |
|------|------|
| **A（必选）** | `pip install -e .\bootstrap[test]` → `bootstrap install-packages` → `bootstrap materialize-workspace … --force` → 用 **`pipeline-workspace-root.env.example`** **覆盖** `{WORKSPACE}\.env` |
| **B（默认全量）** | A + `bootstrap doctor --workspace $WORKSPACE` |

脚本 **省略 `-PythonExe` 时**自动用 **`py -3.12`** 解析出的解释器路径（装有多版本 Python 时无需再把 3.10 设为默认）。仅当机器上 **没有** `py` 启动器或 **没有** 3.12 时，才 fallback 到 `python.exe`（须自行保证 ≥3.12），或显式传 `-PythonExe`。

```powershell
Set-Location <CLONE_ROOT>
powershell -File .\bootstrap\scripts\run-unattended-acceptance.ps1 -SkipDoctor -Workspace "<WORKSPACE>"
```

若要强制指定解释器：

```powershell
$p = py -3.12 -c "import sys; print(sys.executable)"
powershell -File .\bootstrap\scripts\run-unattended-acceptance.ps1 -SkipDoctor -Workspace "<WORKSPACE>" -PythonExe $p.Trim()
```

CI 无私盘可将 **`-Workspace`** 设为 **`%TEMP%\\newvla-bootstrap-unattended-smoke`** 等 **段内无空格** 路径（§3.2）。若维护仓克隆路径本身含空格段（如 `…\\Cursor WorkSpace\\…`），**勿**把物化目录放在该树下当闸门工作区，改选 `TEMP` 或另一 ASCII 无空格目录。

---

## 互链样本

- 结构说明（可提交）：[`docs/superpowers/samples/pipeline-workspace-root.env.example`](../docs/superpowers/samples/pipeline-workspace-root.env.example)

---

## P0 vs CI

**人机签字**以 **Windows** 上 **实拷贝物化**（`vla_env_contract`、`runtime/webhook`、`tools/*`）**与** **工作区内 `pip install -e`** 为准。**Linux CI 绿 ≠** 生产就绪。
