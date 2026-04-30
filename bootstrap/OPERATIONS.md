# 操作手册（人话版）

**定位：** 步骤 / 命令 / 目的速查。**人机签字唯一主路径**仍以根目录 [`README.md`](README.md) 中「用户验收唯一路径」为准；本文件不替代 spec。

---

## 1. 一次性：生成执行工作区

| 步骤 | 命令（示例） | 目的 |
| --- | --- | --- |
| 1 | `Set-Location <CLONE_ROOT>`（维护仓库克隆根） | 保证 `bootstrap` 能认出仓库（需存在 `webhook/pyproject.toml` 与 `bootstrap/pyproject.toml`）。路径含空格时首装 pip 见 [`README.md`](README.md) 第 2 步括号说明（BUG-007）。 |
| 2 | `py -3.12 -m pip install -e ".\bootstrap[test]"` | 安装 `bootstrap` 可编辑包（本仓库要求 Python ≥3.12）；未安装 `py` 时用 Python 3.12 的 `python.exe` 全路径替代。 |
| 3 | `py -3.12 -m bootstrap interactive-setup` | 交互：**确认 clone 根**（不对可贴绝对路径）、**输入执行工作区绝对路径**（与克隆根互不嵌套）；随后冻结顺序：`install-packages` → `materialize-workspace` → `install-workspace-editables` → 提示编辑工作区 `.env` → `doctor` → `probe --no-http`。 |
| 3b | `py -3.12 -m bootstrap interactive-setup --yes` | 同上，但跳过「按 Enter 再跑 doctor」；仍执行 `doctor`。 |
| 4 | 用编辑器打开 `{WORKSPACE}\.env` | **填写密钥与路由**（Dify、飞书、`REDIS_URL` 等）。**`VLA_WORKSPACE_ROOT`** 须与本次选择的执行工作区根目录 **同一规范化绝对路径字符串**，供 webhook/RQ/worker 加载 `{WORKSPACE}/.env`（见 [`README.md`](README.md)「生产启动 webhook / RQ」）。若模板未带来该键，请自行增补，避免交互里选过一次路径、部署时再口头填一次却不一致。 |

---

## 2. 可选：飞书夹级入轨

| 步骤 | 命令（示例） | 目的 |
| --- | --- | --- |
| 1 | `Set-Location <CLONE_ROOT>` | 与 §1 相同：终端 cwd 为**维护仓根**；`feishu-onboard` 据此找 `.env` 与 `rules/`。**默认只写维护仓根 `.env`**；运行侧读 **执行工作区** `.env`，见本表步骤 9。 |
| 2 | 无 `feishu-onboard` 时：`py -3.12 -m pip install -e ".\onboard[test]"` | 本机有可执行入口；已跑过 `bootstrap install-packages` 时通常已装 editable。 |
| 3 | 非 editable 安装时（包在 site-packages）：`$env:FEISHU_ONBOARD_REPO_ROOT="<CLONE_ROOT 绝对路径>"` | 让工具解析到管线仓根；editable 从本仓库装时一般可跳过。 |
| 4 | 编辑维护仓根 `.env` | 必填非空：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID`；对应路线的 **`DIFY_TARGET_<KEY>_`** 整组已齐。 |
| 5 | （准备文件）QA 规则文件已在仓根存在 | 交互里将填相对路径，仅以 `rules/` 或 `prompts/rules/` 开头，禁止 `..` / 绝对路径；与稍后输入 **逐字一致**。 |
| 6 | `Get-Command lark-cli` / `where lark-cli` | 确认 PATH 有 **`lark-cli`**；入轨结束会对仓根跑 `lark-cli config init`。 |
| 7 | （可选）`feishu-onboard verify-delegate --open-id "ou_…"` | 只测建夹 + 协作者，不测 subscribe。 |
| 8 | `feishu-onboard`；必要时 `feishu-onboard --force-new-folder` | 交互填写 `route_key`、`folder_name`、`dify_target_key`、`dataset_id`、`qa_rule_file`、`parent_folder_token`（多数 **父级 token 留空**）。 |
| 9 | 维护仓 `.env` 中新增的 `FEISHU_FOLDER_*`、`FEISHU_FOLDER_ROUTE_KEYS` **合并进** `{WORKSPACE}\.env` | **运行合同**在执行工作区根；不入工作区则进程看不见。 |
| 10 | `py -3.12 -m bootstrap doctor --workspace <WORKSPACE>` | 工作区侧复核路由键组（与 [`README.md`](README.md) / `doctor` 一致）。 |

（`feishu-onboard` 退出码：**0** 成功；**2** 校验/飞书硬错；**3** 部分完成。脱敏与细表见 [`../onboard/README.md`](../onboard/README.md)。）

---

## 3. 部署侧：每台机器上的 Redis、环境与 worker

> **`.venv`：** 生产 **勿** 在 **`{WORKSPACE}/runtime/webhook`**（或工作区其他树）新建并 **依赖** `.venv` 作 Webhook/RQ **正式** 入口；与 **`.cursor/rules/anti-venv.mdc`** 一致。下表 **`$Py`** 为 **`py -3.12`** 或镜像内固定解释器，**非** `runtime\webhook\.venv\Scripts\python.exe`。

| 步骤 | 命令（示例） | 目的 |
| --- | --- | --- |
| 1 | 编辑 `{WORKSPACE}\.env`：按需设置 **`REDIS_URL=...`**（本机 Redis / 托管实例 URL；与真实连接一致）；可选 **`FEISHU_INGEST_DEBOUNCE_SECONDS`**：默认 **0**（关闭）；设为 **60–120** 时，**worker 内**无 `folder_token` 的 ingest 对同一 `document_id` 在去抖窗口内只 **schedule 一次**，合并飞书连续 `drive.file.edit`（仍按 `event_id` 幂等；超窗后的新事件照常单独跑） | RQ / 去重依赖 Redis 时，`doctor` 可 ping；未配则 `doctor` 跳过 Redis 段（见实现）。去抖用 RQ **`enqueue_in`**，worker 须能拉 **scheduled** 任务（默认 `SimpleWorker` 可） |
| 2 | 同上：确认 **`VLA_WORKSPACE_ROOT`** = **本机规范化后的 `{WORKSPACE}` 绝对路径**（与 §1 所选执行工作区 **同一路径字符串**） | **`ExecutorSettings` 等工作区合同**从 `{WORKSPACE}/.env` 读；未设时部分实现会回退读 **克隆根** `.env`（仅 dev 友好），生产勿依赖回退（见 [`README.md`](README.md)「生产启动 webhook / RQ」） |
| 3 | 按你的环境启动 **Redis 服务**（Windows 服务、Docker、`redis-server` 等）或改用远端 URL | 与步骤 1 的 `REDIS_URL` 可达性一致 |
| 3b | **（推荐）重复起服务前先停旧进程：** PowerShell：`& "<CLONE_ROOT>\webhook\scripts\stop_local_runtime.ps1"`；已物化工作区则用 `& "<WS>\runtime\webhook\scripts\stop_local_runtime.ps1"`。可加 `-DryRun` 只打印将结束的 PID。 | 按 **命令行** 匹配本管线 **`uvicorn … build_app`** 与 **`vla:default` RQ worker**，不限 `python.exe` / `py.exe` / `python3.12.exe`，避免「看起来像起了两份」的叠跑。根因级修复见仓库内 `webhook/scripts/stop_local_runtime.ps1`（`test_tool/start_temp_feishu_tunnel.ps1` 里旧清理只认 `python.exe` 的缺陷已另修）。 |
| 4 | **终端 1 — 起 HTTP（`<WS>` = 与 §1 相同的执行工作区根）：**<br>**每终端先固定解释器（推荐，避免多一个 `py.exe` 父进程）：** `$Py = (& py -3.12 -c "import sys; print(sys.executable)").Trim()`<br>`$env:VLA_WORKSPACE_ROOT = "<WS>"`<br>`Set-Location "<WS>\runtime\webhook"`<br>`& $Py -m uvicorn webhook_cursor_executor.app:build_app --factory --host 127.0.0.1 --port 8000` | 与 [`../webhook/操作手册.md`](../webhook/操作手册.md) 第六步 FastAPI 段**同形**；cwd 必须是**工作区**内嵌的 **`runtime\webhook`**。`--port` 与步骤 7 **`WEBHOOK_PROBE_BASE`** 端口一致。 |
| 5 | **终端 2 — 起 RQ worker（`<REDIS>` = 步骤 1 里同一 `REDIS_URL`；队列名与 `.env` 里 `VLA_QUEUE_NAME` 一致，默认 `vla:default`）：**<br>同上先：`$Py = (& py -3.12 -c "import sys; print(sys.executable)").Trim()`<br>`$env:VLA_WORKSPACE_ROOT = "<WS>"`<br>`Set-Location "<WS>\runtime\webhook"`<br>**Windows：** `& $Py -m rq.cli worker -w rq.worker.SimpleWorker vla:default -u "<REDIS>"`（默认 Worker 会 `os.fork`，Windows 无此 API，首条 job 即崩）<br>**Unix：** `& $Py -m rq.cli worker vla:default -u "<REDIS>"`（无 `py` 时把 `$Py` 换成 `python3` 全路径即可） | **`-u`** 即 Redis 连接。**`-w rq.worker.SimpleWorker`** 为 Windows 必加。 |
| 6 | **长期跑：** 用 NSSM / systemd / Docker 等为**上述两个进程**各写一条服务：**环境**里带 **`VLA_WORKSPACE_ROOT=<WS>`**；**工作目录** = **`<WS>\runtime\webhook`**；**可执行行**仍分别是步骤 4、5 里 **`uvicorn`** / **`rq.cli worker`** 两行（勿改 cwd 成维护仓根，除非 legacy JSON 相对路径另有约定，见操作手册第三步）。 | 重启后仍在。勿混用克隆根 `webhook\` 与工作区 `runtime\webhook` 两套 editable。总述见 [`../webhook/README.md`](../webhook/README.md)「执行工作区内嵌路径」。 |
| 7 | **webhook 已在监听后**，编辑 **`{WORKSPACE}\.env`**，一行：<br>`WEBHOOK_PROBE_BASE=http://127.0.0.1:8787`<br>端口改成真实监听端口；**不要**末尾 `/`。 | 给 **`bootstrap probe`** 一个 HTTP 根地址，用来访问 **`/health`**。完成后可用 **§4 步骤 6**。样本：[`pipeline-workspace-root.env.example`](../docs/superpowers/samples/pipeline-workspace-root.env.example)。 |

---

## 4. 自检：doctor 与 probe

| 步骤 | 命令（示例） | 目的 |
| --- | --- | --- |
| 1 | `Set-Location <CLONE_ROOT>` | 与 §1 相同：在维护仓根执行 `python -m bootstrap`（editable 已装）。 |
| 2 | `py -3.12 -m bootstrap doctor --workspace <WORKSPACE>` | 仅 **体检**（Python ≥3.12、`cursor`/`lark-cli`、包导入、嵌入式目录、`.env`、可选 Redis、路由键等），**不包含** HTTP。§1 人机链已含 `doctor` 时可省略；§2 步骤 10 已跑且 `.env` 未改可省略。 |
| 3 | `py -3.12 -m bootstrap probe --workspace <WORKSPACE>`（**不传** `--skip-doctor` / `--no-http`） | **先**跑一遍 **`doctor`**（与步骤 2 重复一次）；随后若工作区 `.env` **未**设 **`WEBHOOK_PROBE_BASE`** 且未传 **`--webhook-http-base`** → **退出码 1**（HTTP 段报「skipped unsuccessfully」）；若已设且 webhook 已监听 → **`GET …/health`** 预期 **200** |
| 4 | `py -3.12 -m bootstrap probe --workspace <WORKSPACE> --no-http`（**不传** `--skip-doctor`） | **先** **`doctor`**；再 stderr 打 **RQ 未检测** 类 WARNING；**不访问 HTTP**，退出 **0**（与「只要体检、暂不要求 webhook 已起」一致） |
| 5 | `py -3.12 -m bootstrap probe --workspace <WORKSPACE> --skip-doctor --no-http` | **不跑** **`doctor`**；WARNING 后退出 **0**；**不访问 HTTP**。**`interactive-setup` 人机链末尾**即是此组合（链内已跑过 `doctor`） |
| 6 | `py -3.12 -m bootstrap probe --workspace <WORKSPACE> --skip-doctor`（**不传** `--no-http`） | **不跑** **`doctor`**；必须有 **`WEBHOOK_PROBE_BASE`**（或 **`--webhook-http-base`**），否则 **退出码 1**；否则 **`GET /health`**。用于 **§3 已起 webhook** 且 **§2/步骤 2 已跑过 doctor** 后的 **投产探活** |

（`pip` 仅以 wheel 安装、**`--clone-root` 无法自动推导**时，上述命令一律加 **`--clone-root <CLONE_ROOT>`**。退出码总表见 [`README.md`](README.md)「`bootstrap probe` 退出码」。）

---

## 5. 分立子命令（CI / 排障）

以下**不**作为与人验收并列的第二套主入口，仅脚本与排障：`install-packages`、`materialize-workspace`、`install-workspace-editables`、`doctor`、`probe`。说明见 [`README.md`](README.md) 开篇。

---

## 6. 一句话串联

维护仓 **`interactive-setup`** → **执行工作区 `.env`** → **按需 §2 入轨并合并** → **§3 起 Redis / webhook / worker** → **§4 `doctor` / `probe`**。
