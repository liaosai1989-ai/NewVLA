# Production Bootstrap（执行工作区物化）

## 用户验收唯一路径（签字）

与 `docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md` §7 一致：**不得**用分立子命令替代本条作为主签字路径。

1. `Set-Location <CLONE_ROOT>`（维护仓库克隆根）。
2. `py -3.12 -m pip install -e ".\bootstrap[test]"`（本仓库 **`requires-python >=3.12`**；未装 `py` 时用 **Python 3.12** 的 `python.exe` 全路径）。**克隆路径某段含空格**且本条报 **`No such file or directory`**、错误路径像 **`...\父级\onboard`**（少仓库名一级）：改 **`Set-Location .\bootstrap`** → **`py -3.12 -m pip install -e ".[test]"`** → **`Set-Location ..`**（根因见 `BugList.md` **BUG-007**；`install-packages` / 闸门脚本已用等价安全调用）。
3. `py -3.12 -m bootstrap interactive-setup`（冻结顺序：`install-packages` → `materialize-workspace` → **`install-workspace-editables`**（四轮工作区 `pip install -e .`）→ 提示编辑 **`{WORKSPACE}\.env`** → `doctor` → **`probe --no-http`**（不起 HTTP 监听时仅 doctor + 可选 RQ 告警段））。

运行合同 **`.env` 只在「执行工作区根」**；物理路径 **仅**由交互/`--workspace` 表达。**勿**在工作区 `.env` 增加 `PIPELINE_WORKSPACE_PATH` 等与 CLI 重复的路径抽象。

分立子命令 **`install-workspace-editables`**、`doctor`、`install-packages`、`materialize-workspace`、**`probe`**：**仅** CI、脚本与排障补充；**不得**替代上面第 3 条作为与人验收并列的「第二套主入口」。

### PowerShell（勿用 bash `` `&&` ``）

```powershell
Set-Location <CLONE_ROOT>
py -3.12 -m pip install -e ".\bootstrap[test]"
py -3.12 -m bootstrap interactive-setup
```

物化后按提示用编辑器打开工作区 `.env` 填入密钥；再继续直至 `doctor` 与交互内 `probe`（`--no-http`）结束。**起 webhook 后**可在同工作区另行执行 **`bootstrap probe --workspace …`**（**不带** `--no-http`）以对 `{WEBHOOK_PROBE_BASE}/health` 做全流程 HTTP 探活（见工作区 `.env` 中 **`WEBHOOK_PROBE_BASE`**，`http://127.0.0.1:<PORT>` 级）。

**工作区内四轮 `pip install -e .` 唯一写法（不要手抄四条 PowerShell）：** 子命令 **`bootstrap install-workspace-editables --workspace <WORKSPACE>`**，顺序固定为 **`vla_env_contract`** → **`runtime/webhook`** → **`tools/dify_upload`** → **`tools/feishu_fetch`**。

---

## `bootstrap probe` 退出码

| 退出码 | 含义 |
|--------|------|
| **0** | `doctor` 通过（未使用 `--skip-doctor` 时）；且 **`--no-http`** 时跳过 HTTP；或 HTTP GET **`{WEBHOOK_PROBE_BASE}/health`** 得到 **200** |
| **1** | `doctor` 未通过；或需要 HTTP 时 **`WEBHOOK_PROBE_BASE` 与工作区 `.env` 均无有效基地址**且无 **`--webhook-http-base`**；或 **TCP/HTTP 失败**、非 200 |
| **2** | **`--clone-root` 无效**（与其它子命令一致的克隆根自检失败） |

**`--no-http`（交互与非 HTTP 闸门）：** 仅跑 `doctor`（除非同时传 **`--skip-doctor`**），不访问 webhook；stderr 可出现 **RQ 探测未实现** 的一行 WARNING。

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
| BUG-007（Windows / `pip` / 路径含空格） | 克隆侧 **`install-packages`** 与各包 **`cwd` + `-e .`**；工作区四轮 **`bootstrap install-workspace-editables`**；**`run-unattended-acceptance.ps1`** 在 **`bootstrap` 目录内** 首装。人手在克隆根首装仍遇 **`file:../onboard`** 错位时按上文第 2 步括号说明；排障与复现命令见 `BugList.md` |
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

**不替代人机签字。** Merge/CI 常用 **A 档**：**不写盘医生** **`-SkipDoctor`**，且通常 **不写盘 HTTP `-SkipProbe` 或不监听 webhook 时使用 `-SkipProbeHttp`**。**B 档**在本机已有 **cursor / lark / Redis** 等前提下跑 **`doctor`**，并在 webhook 已监听后对 **`probe`（HTTP）** 签字。闸门脚本对 **`materialize-workspace` 带 `--force`**；同一 **`Workspace`** 重复跑不会因残留 **`rules/`** 失败。

**闸门冻结顺序：** `pip install -e .\bootstrap[test]`（在 **`bootstrap`** 目录内执行，见上文 BUG-007）→ **（可选）** **`bootstrap install-packages`** → **`bootstrap materialize-workspace … --force`** → **`bootstrap install-workspace-editables --workspace`** → 用 **`pipeline-workspace-root.env.example`** **覆盖** `{WORKSPACE}\.env` → **`doctor`**（若未 `-SkipDoctor`）→ **`probe`**（`-SkipProbeHttp` **仅跳过 HTTP 段**，不是全流程签字等价物；`-SkipProbe` 整条跳过 **`probe`**）

**`-SkipInstallPackages` 默认为 `$true`：** **不**跑克隆侧 **`bootstrap install-packages`**（避免克隆 editable 与工作区 **`doctor`** 的包前缀混淆）；需要时传 **`-SkipInstallPackages:$false`**。

| 档位 | 内容 |
|------|------|
| **A（Merge/CI 常见）** | 上序列 + **`-SkipDoctor`**；建议 **` -SkipProbe`**（或 **`-SkipProbeHttp`** 仅 **`probe --no-http`**）。**≠** B 档全流程 |
| **B（机器上全量）** | 含 **`doctor`**；**不带** `-SkipProbeHttp` 时 **`probe` 会对 `WEBHOOK_PROBE_BASE`/health**（须 webhook 已在对应端口监听） |

脚本 **省略 `-PythonExe` 时**自动用 **`py -3.12`** 解析出的解释器路径（装有多版本 Python 时无需再把 3.10 设为默认）。仅当机器上 **没有** `py` 启动器或 **没有** 3.12 时，才 fallback 到 `python.exe`（须自行保证 ≥3.12），或显式传 `-PythonExe`。

```powershell
Set-Location <CLONE_ROOT>
powershell -File .\bootstrap\scripts\run-unattended-acceptance.ps1 -SkipDoctor -SkipProbe -Workspace "<WORKSPACE>"
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
