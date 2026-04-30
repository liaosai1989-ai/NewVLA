# Bug 清单

## 填写规范

> 用途：记录本仓库已知缺陷、回归与排障结论。  
> 填写顺序：先补 **Bug 总表**，再写 **正文** 对应条目。  
> 适用：登记 bug 的维护者与 agent。

### 规则

- 新 bug：先在 `Bug 总表` 增一行，再在 `正文记录` 增一条（标题 `## BUG-XXX 摘要`）。
- `ID` 递增：`BUG-001`、`BUG-002`、…
- `严重级别`：`P0`（阻塞/数据丢失/安全）｜`P1`（主要功能受损）｜`P2`（次要/有绕过）｜`P3`（文案/体验/非阻塞）
- `状态`：`待复现`｜`已确认`｜`修复中`｜`已修复`｜`待验证`｜`已关闭`｜`不修复`（不修复须写清原因）
- `相关链接`：issue、PR、spec/plan 路径；无则填 `-`
- 修复并验证后：总表与正文同步改状态；**不删**历史条目，可补充「关闭说明/验证方式」
- 与 `NiceToHave.md` 区分：此处只记**已发生或已确认的问题**；**愿望项**进 NiceToHave

### 正文条目模板

````md
## BUG-XXX 一句话摘要

- 发现时间：
- 当前状态：
- 严重级别：
- 环境/复现：版本、OS、复现步骤（可列表）
- 现象：
- 预期：
- 根因（若已定位）：
- 相关链接：

### 修复说明（有则填）

- 

### 验证（关闭前填）

- 
````

## Bug 总表

| ID | 摘要 | 严重级别 | 状态 | 发现时间 | 相关链接 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| BUG-001 | 可执行文件依赖应统一为 PATH+标准解析，需全仓审计历史旁路 | P2 | 已确认 | 2026-04-27 | `onboard/README.md`、`onboard/.../lark_cli.py`、`feishu_fetch/.../facade.py`、`webhook/.../cursor_cli.py`/`settings.py`、`webhook/操作手册` 升级节、`docs/superpowers/specs/2026-04-26-webhook-cursor-executor-design.md` 修订 2026-04-27 | `webhook` 已：固定 `cursor`+`which`、禁 `CURSOR_CLI_COMMAND`；`feishu_fetch`/`onboard` 同前；**全仓**余模块审计关单仍待 |
| BUG-002 | 入轨 `POST .../permissions/.../members?type=folder` 在联调子命令可成功时仍 400/失败，属表现差异需收敛 | P1 | 已关闭 | 2026-04-27 | `onboard/src/feishu_onboard/flow.py`、`onboard/src/feishu_onboard/feishu_client.py` | 关闭：根因为 `.env` 中委托人 `open_id` 抄录少一位 → 1063001；修正后加协作者成功 |
| BUG-003 | `lark-cli config show` 误传 `--json`，与 @larksuite/cli 1.0.19 不符，致校验子进程退出码 1 | P1 | 已修复 | 2026-04-27 | `onboard/src/feishu_onboard/lark_cli.py`、`feishu_fetch/src/feishu_fetch/facade.py` | 改为 `config show`；`onboard`/`feishu_fetch` 单测与真机入轨可验 |
| BUG-004 | `feishu-onboard` 与 webhook 对同一路线双重登记 `qa_rule_file`/`dataset_id`，v1 运行时只消费 JSON 侧字段，易与根 `.env` 展示脱节 | P2 | 已关闭 | 2026-04-27 | `webhook/操作手册.md`、`onboard/flow.py` | 关闭：webhook **`FEISHU_FOLDER_ROUTE_KEYS`** 与各 **`FEISHU_FOLDER_<KEY>_*`** 为运行时 mapping 真源，与 onboard 对齐；见 BUG-005 同源修复 |
| BUG-005 | webhook 以 `FOLDER_ROUTES_FILE` JSON 为 folder 路由运行时来源，违反本仓「根 `.env` 唯一真源」约定（与 onboard / 其余模块不一致） | P1 | 已关闭 | 2026-04-27 | `.cursor/rules/env.mdc`、`webhook/.../settings.py` `load_routing_config` | 关闭：**`FEISHU_FOLDER_ROUTE_KEYS` 非空**时从工作区 `.env` 构造路由；JSON legacy + 告警；RQ/`ingest_kind` 见 task-context spec |
| BUG-006 | `feishu-onboard` 建应用文件夹后**未**调用飞书「夹级事件订阅」OpenAPI，缺 `file.created_in_folder_v1` 等前提，与同应用下能稳定收 `drive.file.edit_v1` 的栈（如含 subscribe 流程）表现不一致 | P1 | 已修复 | 2026-04-27 | `onboard/.../feishu_client.py` `subscribe_folder_file_created`、`flow.py`；**编辑事件**另需 webhook **事件驱动 per-doc** `subscribe`（`feishu_drive_subscribe.py`，2026-04-29） | 夹级 + `created_in_folder` 后 tenant 对 `file_token` 补订；**禁止**夹内历史全量枚举；**不**用户 OAuth |
| BUG-007 | 在克隆根或非包根 `cwd` 执行 `pip install -e .\子包`，`pyproject` 同源 **`file:`** 依赖（如 **`vla-env-contract @ file:../vla_env_contract`**；历史示例含 `feishu-onboard @ file:../onboard`）被解析错位，editable 安装失败 | P2 | 已修复 | 2026-04-28 | `bootstrap/scripts/run-unattended-acceptance.ps1`、`bootstrap/src/bootstrap/install_packages.py`、`bootstrap install-workspace-editables`、`bootstrap/README.md`、`bootstrap/tests/test_install_packages.py`、`webhook/pyproject.toml`、[2026-04-28-workspace-embedded-runtime-implementation-plan.md](docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md)、[2026-04-28-production-bootstrap-deployment-implementation-plan.md](docs/superpowers/plans/2026-04-28-production-bootstrap-deployment-implementation-plan.md) §Task 14 | 缓解：克隆侧 `install_packages` **`cwd`+`-e .`**；**生产工作区**须在 **`vla_env_contract`、`runtime/webhook`、`tools/dify_upload`、`tools/feishu_fetch`** 各目录 **`pip install -e .`**（**`bootstrap install-workspace-editables --workspace`**）。**工具链**「克隆根 + 子包绝对路径 `-e`」仍可能复现；首装见 README |
| BUG-008 | 合同与样例未在同处写清：`run_id`**字面值**无 UUID/时间戳强制；**生产**宜每任务唯一、低冲突；**仓库样例**用固定名（如 `bootstrap-sample-run`）——易被判「未按规范命名」 | P3 | 已关闭 | 2026-04-28 | [.cursor/rules/workplacestructure.mdc](.cursor/rules/workplacestructure.mdc)、[2026-04-28-task-context-bootstrap-sample-agent-contract-design.md](docs/superpowers/specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) §3.1、`docs/superpowers/samples/task_context.bootstrap.example.json` | 关闭：§3.1 + workplacestructure 互链 |

## 正文记录

> 按 `ID` 升序，标题为 `## BUG-XXX 一句话摘要`。

## BUG-006 `feishu-onboard` 建应用文件夹后未调飞书 OpenAPI「夹级 subscribe」（`file.created_in_folder_v1` 前提），与同应用能推编辑事件的栈不一致

- 发现时间：2026-04-27
- 当前状态：已修复
- 严重级别：P1
- 环境/复现：同一飞书应用、同租户；两个云文件夹分别由 **`feishu-onboard`（本仓）** 与 **含 subscribe 的管线（如 `VDBP-library-Automation`）** 建夹/入轨；仅对「经 onboard 的夹」在开放平台 **事件/投递** 中长期无或不稳定 **`drive.file.edit_v1`**，另一只夹可正常推。
- 现象：起初易误判为「路由 / webhook / 两夹元数据」问题；**对问题夹补** `POST https://open.feishu.cn/open-apis/drive/v1/files/{folder_token}/subscribe` 且 `file_type=folder`、`event_type=file.created_in_folder_v1`（并确保开发者后台已添加对应事件 type）后，**推送恢复**，可反证非「本机 webhook 不接收该夹」这一层单点。
- 预期：经 onboard 新建的应用文件夹具备 **夹级** subscribe；**新建文件**后由 **webhook 在 `drive.file.created_in_folder_v1` 上事件驱动** 对该 `file_token` 做 **tenant per-doc** subscribe（见 `webhook_cursor_executor.feishu_drive_subscribe`）。**禁止**夹内历史 **全量枚举** subscribe；**不**用用户 OAuth。
- 根因（已定位）：`onboard` 的 `FeishuOnboardClient` / `flow.run_onboard` 在 **`create_folder`、加协作者** 后 **无** 上述「夹级 subscribe」调用；[对比] `VDBP-library-Automation` 的 `vla/feishu/client.subscribe_folder_file_created` 等。另：仅夹级不足以稳定 **`drive.file.edit_v1`**，须 worker 在 created_in_folder 后补 per-doc subscribe（2026-04-29 合入）。
- 相关链接：上文总表；`webhook/scripts/subscribe_byvwf_tds.py`（**仅**夹级 subscribe 的参考调用，**非**长期枚举 doc）；根 `.env` 中 `FEISHU_APP_*`；飞书《文件夹下文件创建》事件体含 `folder_token` 等（与 `drive.file.edit_v1` 无 `folder_token` 行为不同，webhook 侧已另有列目录/ingest 逻辑）。

### 修复说明（有则填）

- `FeishuOnboardClient.subscribe_folder_file_created`：`POST .../drive/v1/files/{token}/subscribe?file_type=folder&event_type=file.created_in_folder_v1`（与 `webhook/scripts/subscribe_byvwf_tds.py` 一致）。`run_onboard` 在取得 `folder_token`（新建或复用已有 route）后、**`add_folder_user_collaborator` 前** 调用；失败走既有 `FeishuApiError` 路径，不静默。未做「枚举夹内旧 docx」。**Webhook**：`drive.file.created_in_folder_v1` 处理链上 **`feishu_drive_subscribe.event_driven_per_doc_subscribe`**（tenant、按事件体 `file_type`）；**禁止** worker 对夹内历史全量扫 subscribe。

### 验证（关闭前填）

- `onboard` 下 `python -m pytest tests/` 全绿（本机 `.venv`）。生产租户建议再跑一次入轨或对手动 token 调 subscribe 在开放平台看投递。
- 文档：已同步 `docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md`（修订说明）、`docs/superpowers/plans/2026-04-27-feishu-app-folder-onboard-implementation-plan.md`（修订说明）、`docs/superpowers/specs/2026-04-26-feishu-fetch-lark-cli-*.md` / 同名 workspace-init、`onboard/README.md` / `onboard/操作手册.md`、`webhook/操作手册.md`、`webhook/阶段性验收手册.md`、根 `AGENTS.md`。

## BUG-002 入轨 `POST .../permissions/.../members?type=folder` 在联调子命令可成功时仍 400/失败，属表现差异需收敛

- 发现时间：2026-04-27
- 当前状态：已关闭
- 严重级别：P1
- 环境/复现：根 `.env` 同应用；`feishu-onboard verify-delegate` 可成功加协作者，整段 `feishu-onboard` 入轨在相同步骤上失败或曾出现 HTTP 400。
- 现象：与「仅子命令能通」不一致，**不能**用「代码自洽」代回复现。
- 预期：同凭据、同 `folder_token`（或等价新夹）上行为可解释、错误信息含飞书业务 `code/msg`。
- 根因（已定位）：`FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID` 抄录时 **少一位**（`ou_` 后应为 32 位十六进制），飞书返回 **1063001** Invalid parameter。非 verify-delegate 与入轨逻辑不一致；此前「子命令可通」与「整段失败」若凭据/委托人同一，需对照当时 `.env` 是否续跑时委托人键被改或未重载。
- 相关链接：上文总表

### 修复说明（有则填）

- `feishu_client.add_folder_user_collaborator`：对 HTTP 4xx **不再** `raise_for_status()`，业务错误走 `code/msg` 回传；URL 中 `folder_token` **strip**。
- `flow.run_onboard`：新建后 **strip** `folder_token`；阶段 A `set_keys_atomic` 后 **重读**根 `.env` 再取委托人三键；续跑加人失败时 **追加**提示（占位/失效 TOKEN、建议 `--force-new-folder`）；若重读后无委托人则 **显式失败**防静默错。

### 验证（关闭前填）

- 已验证（2026-04-27）：补全委托人 `open_id` 后，入轨侧 **已为文件夹成功添加分享委托人协作者**；后续由该用户在飞书客户端打开文件夹，将「分享」可见范围调为组织内/全员等（与 `onboard/操作手册.md` 一致）。

## BUG-001 可执行文件依赖应统一为 PATH+标准解析，需全仓审计历史旁路

- 发现时间：2026-04-27
- 当前状态：已确认（`onboard` 已按标准实现调整；**全仓库**对同类问题的排查**待做**）
- 严重级别：P2
- 环境/复现：
  - 背景：部分代码在 **PATH 无法写入/不可靠** 的环境下开发，曾以非标准方式「绕过」（例如本机可执行文件**硬编码/非 PATH 配置**的隐性约定，而非仓库内可审查契约）。
  - 表现：`lark-cli`、`node`、`markitdown` 等若未统一从 **PATH** 与语言侧标准解析（如 Python 的 `shutil.which`）解析，则换机、CI 与协作者环境易出现**偶发找不到命令**，且与**规范环境约定**（应用内不写死可执行文件路径、由运行环境提供 PATH）不一致。
- 现象：在 `feishu-onboard` 入轨与排障中暴露；同一类风险可能存在于**其他子模块**（如 `feishu_fetch` 等对 `lark-cli`、Python `markitdown` 的调用方式）。
- 预期：全仓库中 **调用外部可执行文件或 CLI** 的代码路径，应统一为：**依赖 PATH、文档说明由运维/本机配好环境**；不依赖未文档化的本机旁路、不在应用配置中塞「绝对路径可执行文件」作为长期方案。
- 根因（已讨论结论）：**历史环境与代码质量**导致旁路，不应在维护仓库内延续；应在实现与文档中强制标准约定。
- 相关链接：
  - `onboard/README.md` §4（`lark-cli` 与 PATH）
  - `onboard/src/feishu_onboard/lark_cli.py`（仅 `shutil.which` + `lark-cli`）
  - 待扫示例：`feishu_fetch`（`lark-cli`、`markitdown` 等），见全仓 `grep`/架构审查

### 修复说明（有则填）

- `onboard`：`flow` 固定命令名 `lark-cli`，**不**读 `LARK_CLI_COMMAND`；`lark_cli._resolve_lark_cli_exe` 仅 `shutil.which`。其余包待按本条做**全仓库检查**后更新状态。
- `feishu_fetch`：与 [2026-04-27-feishu-fetch-lark-cli-workspace-init-implementation-plan.md](docs/superpowers/plans/2026-04-27-feishu-fetch-lark-cli-workspace-init-implementation-plan.md) 一致；包内无 `MARKITDOWN_COMMAND`、无 lark 外可执行 `*_COMMAND` 旁路；lark 不经 `FeishuFetchSettings`，`LARK_CLI_COMMAND` 在 `.env` 中视为废键；`lark-cli`+`shutil.which`+`subprocess.run(..., cwd=workspace_root)`。全仓关单仍依总表条件。
- `webhook`：固定 `cursor` + `shutil.which`；`CURSOR_CLI_COMMAND` 已从设置模型移除，根 `.env`/环境变量出现该键则启动失败；`cursor_not_in_path` 见 `操作手册` 排障。spec/plan 已追加 2026-04-27 修订说明与升级阻断说明。

### 验证（关闭前填）

- 关闭本 bug 的合理条件建议：**全仓审计完成**、列出已扫描路径与结论（或建子 issue/PR 追踪），并确认无未文档化的可执行文件旁路；或经团队决议接受例外并**写入文档**。

## BUG-003 `lark-cli config show` 误传 `--json`，与 @larksuite/cli 1.0.19 不符，致校验子进程退出码 1

- 发现时间：2026-04-27
- 当前状态：已修复
- 严重级别：P1
- 环境/复现：`@larksuite/cli` 1.0.19（例：`npm list -g @larksuite/cli`）；`lark-cli config show --help` 仅含 `-h`；执行 `lark-cli config show --json` 报 `unknown flag: --json`，退出码非 0。
- 现象：`feishu-onboard` 在 `lark_config_init` 成功后调用 `lark_config_show_verify_app_id`，子进程 argv 含 `config show --json`，失败文案含 `lark 子进程失败: 退出码=1`；`feishu_fetch` 预检同样使用 `--json`。
- 预期：与官方 CLI 一致，仅调用实际存在的子命令/参数；对 `config show` 自 stdout 解析 JSON（官方该版本默认输出即为 JSON）。
- 根因（已定位）：实现误用不存在的 `--json`；非凭据错误、非「未安装 lark-cli」。
- 相关链接：`onboard/src/feishu_onboard/lark_cli.py`、`feishu_fetch/src/feishu_fetch/facade.py`、`feishu_fetch/tests/fixtures/mock_lark_cli.py`、`feishu_fetch/README.md`；官方包 <https://www.npmjs.com/package/@larksuite/cli>

### 修复说明（有则填）

- 将 `lark_config_show_verify_app_id` / 预检 argv 改为 **`config show`**（不传 `--json`），仍对 stdout 做 JSON 解析与 `appId` 比对。

### 验证（关闭前填）

- 已验证：代码已改为 `config show`（无 `--json`）；`onboard` / `feishu_fetch` 相关 `pytest` 通过；`feishu-onboard` 可完成阶段 B（终端出现「成功，已写入阶段 B 索引」、退出码 0）。

## BUG-004 `feishu-onboard` 与 webhook 对同一路线双重登记 `qa_rule_file`/`dataset_id`，运行时仅 JSON 生效，易与根 `.env` 脱节

- 发现时间：2026-04-27
- 当前状态：已关闭
- 严重级别：P2
- 环境/复现：完成 `feishu-onboard` 入轨后根 `.env` 含 `FEISHU_FOLDER_<KEY>_QA_RULE_FILE`、`..._DATASET_ID`、`..._TOKEN`；webhook 进程读 `FOLDER_ROUTES_FILE` 指向的 JSON（`folder_routes[]`），不读取上述 `.env` 键。
- 现象：运维只改 `.env` 或只改 JSON 一侧时，线上注入与「应在 `.env` 里看到的真值」不一致；人若以 `.env` 为准会误判（**与 BUG-005 同根：v1 实现未以 `.env` 为路由真源**）。
- 预期：与仓库约定一致——**根 `.env` 唯一真源**，不在 JSON 里维护第二套业务映射。
- 根因（已定位）：v1 `load_routing_config` 仅从 JSON 读 `folder_routes`；onboard 按约定写 `.env`；实现未合并。
- 相关链接：
  - **BUG-005**（真源约定冲突总述）
  - `webhook/操作手册.md` 第四步
  - `docs/superpowers/specs/2026-04-26-webhook-cursor-executor-design.md`、`NiceToHave.md`（NTH-002 等）

### 修复说明（有则填）

- **2026-04-28：** `webhook_cursor_executor.settings.load_routing_config`：**`FEISHU_FOLDER_ROUTE_KEYS` 非空**则从工作区 `.env` 推导 `folder_routes`，与 **`onboard`/五键同质**（含 `NAME`）。不再要求运维为同一路线同时在 JSON「再维护一套」作为主真源。**关单连带 BUG-005。**

### 验证（关闭前填）

- `cd webhook`; `pytest` 通过；启用 `.env` 路由后单次任务 `task_context.json` 与 `.env` 中该 route **一致**。手册见 `webhook/操作手册.md` 第四步（首选）。

## BUG-005 webhook 以 `FOLDER_ROUTES_FILE` JSON 为 folder 路由运行时来源，违反本仓「根 `.env` 唯一真源」约定

- 发现时间：2026-04-27
- 当前状态：已关闭
- 严重级别：P1
- 环境/复现：仓库规则 `.cursor/rules/env.mdc`、根 `AGENTS.md` 均约定**项目根 `.env` 为唯一真源**；`onboard`、`feishu_fetch`、`dify_upload` 等按该约定从 `.env` 取业务配置。运行 `webhook_cursor_executor` 时，`resolve_folder_route` 使用的 `folder_routes` 来自 `load_routing_config` → **仅读取 JSON 文件**，不解析 `FEISHU_FOLDER_<KEY>_*`。
- 现象：文档/手册若写「.env 台账、JSON 真源」会把**错误语义**合理化；实际与全仓约定相反——**应以 `.env` 为真源**，当前实现是例外债。
- 预期：webhook 路由命中结果由根 `.env` 中显式 route 索引与 `FEISHU_FOLDER_*` 分组推导（与 `2026-04-26-root-env-and-dify-target-contract-design.md`、`2026-04-26-webhook-cursor-executor-design.md` 修订方向一致）；`folder_routes.example.json` 仅示例或由 `.env` 导出，不作运行时真源。
- 根因（已定位）：v1 实现先落地 JSON 加载；与后续「全仓 `.env` 合同」收敛未完成。
- 相关链接：
  - `.cursor/rules/env.mdc`
  - `webhook/src/webhook_cursor_executor/settings.py`、`app.py`（`load_routing_config` / `resolve_folder_route`）
  - `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md`
  - **BUG-004**（双重登记运维后果）
  - `NiceToHave.md` NTH-002 等

### 修复说明（有则填）

- **2026-04-28：** 生产路径 **`FEISHU_FOLDER_ROUTE_KEYS` + `FEISHU_FOLDER_<KEY>_*`**；**仅当 ROUTE_KEYS 未配置**时回退 **`FOLDER_ROUTES_FILE`** 并告警。与 **[2026-04-28-task-context-bootstrap-sample-agent-contract-design.md](docs/superpowers/specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md)** §7、[2026-04-26-webhook-cursor-executor-design.md](docs/superpowers/specs/2026-04-26-webhook-cursor-executor-design.md) 文首本批次修订说明一致；HTTP/RQ **`ingest_kind`** 显式写入 `task_context.json`。

### 验证（关闭前填）

- `cd webhook`; `pytest` 全绿；根 `.env` 配齐 **ROUTE_KEYS** 与两段 route **五键** 后，不因 JSON 漂移而改变命中（可无 JSON 或占位）。legacy 单列测 / 告警行为以 `tests/test_settings.py` 为准。

## BUG-007 克隆根运行 `pip install -e .\子包目录`（绝对路径 editable）时同源 **`file:`** 依赖解析错位（历史：`file:../onboard`；现行：`file:../vla_env_contract` 等），本地依赖安装失败

- 发现时间：2026-04-28
- 当前状态：已修复（仓库内引导路径与 `install-packages`、**工作区 `install-workspace-editables`** 已缓解；**手动**在克隆根对子包传 **绝对路径** `-e` 仍可能触发 pip 行为，见验证）
- 严重级别：P2
- 环境/复现：**Windows**。维护仓库_clone 路径含 **空格**典型（例如 `...\Cursor WorkSpace\NewVLA`）。从 **克隆根** 执行：`python -m pip install -e "<CLONE>\webhook"`（或 pip 将 editable 目标解析为**子包绝对路径**时）。同机 **`Set-Location` 进入包根目录** 后再 `pip install -e "."` → **成功**。
- 现象：**errno 2**、`No such file or directory`，日志中出现的待处理路径可能 **丢掉路径中间段**（历史示例：`...\Cursor WorkSpace\onboard` 缺 `NewVLA`）；或对 **`runtime/webhook`** 安装时 **`file:../../vla_env_contract`**（物化后）须在 **该包根 `cwd`** 下解析。**非** 凭据缺失、**非** 源码树不存在。
- 预期：**PEP 508** 期望 `pyproject.toml` 同目录相对 **`file:`** URL 以 **声明该依赖的包根** 为锚；**每次 `pip install -e .` 的 `cwd` 须为该包根**。**生产签字（内嵌 runtime）：** 须在 **`{WORKSPACE_ROOT}/vla_env_contract`、`{WORKSPACE_ROOT}/runtime/webhook`、`{WORKSPACE_ROOT}/tools/dify_upload`、`{WORKSPACE_ROOT}/tools/feishu_fetch`** 各执行一次 **`pip install -e .`**（顺序见 **`bootstrap install-workspace-editables`** / [workspace-embedded-runtime-implementation-plan](docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md)）。
- 根因（已归纳）：**pip / 构建后端**在 **`install -e` 目标传入「自父级解析的绝对路径」**（且 Windows 路径分段含空格等情况）时对 **`file:`** 本地依赖的展开 **与 **`cd`** 进包根再 `-e .`** **不一致**。属 **工具链兼容性**。
- 相关链接：`bootstrap/scripts/run-unattended-acceptance.ps1`、`bootstrap/src/bootstrap/install_packages.py`、`bootstrap/README.md`（路径含空格说明）；[2026-04-28-workspace-embedded-runtime-implementation-plan.md](docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md)；上文总表。

### 修复说明（有则填）

- **`bootstrap/src/bootstrap/install_packages.py`：** `_pip_run` 支持 `cwd`；`install_all` 对每个子包使用 **`cwd=str(pkg.resolve())` + `pip install -e .`**，不再向 pip 传入子包目录的绝对路径作为 `-e` 唯一实参。
- **`bootstrap/scripts/run-unattended-acceptance.ps1`：** **`Push-Location`** 至 **`bootstrap`**，执行 **`pip install -e ".[test]"`**，再 **`Pop-Location`**；物化后调用 **`bootstrap install-workspace-editables --workspace`**（工作区四处 editable）。
- **`bootstrap/tests/test_install_packages.py`：** 断言 editable 调用带正确 `cwd` 与顺序；`markitdown` 调用无 `cwd`。

### 验证（关闭前填）

- **复现（工具链仍存）：** Python **≥3.12** 新 venv，`Set-Location <CLONE_ROOT>`，执行  
  `python -m pip install -e "<CLONE_ROOT>\webhook"`  
  在含空格克隆根上仍可出现路径段丢失类错误（具体缺段随 **`file:`** 依赖而变）。
- **修复路径（克隆侧）：** 同上 venv，`Set-Location <CLONE_ROOT>\bootstrap`，`python -m pip install -e ".[test]"`，回到克隆根后  
  `python -m bootstrap install-packages --clone-root "<CLONE_ROOT>"`  
  应 **exit 0**。
- **修复路径（工作区侧）：** `materialize-workspace` 后 **`python -m bootstrap install-workspace-editables --workspace "<WORKSPACE_ROOT>"`**，`doctor --workspace` 通过。
- **单测：** `python -m pytest bootstrap/tests/test_install_packages.py` 通过。

## BUG-008 规范未并拢写：`run_id` 格式自由度、生产「每任务唯一」与仓库样例「固定可读名」易混读

- 发现时间：2026-04-28
- 当前状态：已关闭
- 严重级别：P3
- 环境/复现：阅读 `.cursor/rules/workplacestructure.mdc`（约定 `.cursor_task/{run_id}/`）、[`2026-04-28-task-context-bootstrap-sample-agent-contract-design.md`](docs/superpowers/specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md)（表字段「`run_id` 与目录一致」）、[`task_context.bootstrap.example.json`](docs/superpowers/samples/task_context.bootstrap.example.json)（`run_id`: `bootstrap-sample-run`）；对比生产预期「webhook 每次任务新发 id」的讨论。
- 现象：读者易误解为 **`run_id` 必须**某种形态（UUID/前缀 `run_` 等），或反将 **样例固定名判为不合规**。实际：**规范要求的是目录名 ⇔ JSON 字段一致**；对**字面值本体**未见强制 UUID/时间戳。**生产路径**与一般调度实践：每次任务 **`run_id`** 应 **新发、不易冲突**（具体算法实现定）。**文档样例**为可重复对照，刻意 **固定可读字符串**合规。
- 预期：**同一 spec/README 条目**（或互链脚注）并拢写清三句：(1) 结构约束：`.cursor_task/{run_id}/` 与 `task_context.run_id` 一致；(2) **不**规定 `run_id` 必须为 UUID；(3) **生产**Webhook/调度注入应 **按任务生成**唯一/低冲突 **`run_id`**；(4)**本仓库提交的 JSON 样例**可为 **稳定常量**以利回归。
- 根因：**规范分散**、`run_id` 语义（格式 vs 唯一性义务 vs 样例特例）未在单处显性编号，属**文档契约缺口**，非运行时 bug。
- 相关链接：此文总表；[`webhook/.../task_files.py`](webhook/src/webhook_cursor_executor/task_files.py) `write_task_bundle`（以调用方传入 `run_id` 为准）。

### 修复说明

- [`2026-04-28-task-context-bootstrap-sample-agent-contract-design.md`](docs/superpowers/specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) 文首 **修订说明** + **§3.1** 四条编号规则；§3 表 **run_id** 行指向 §3.1；§4 互链 **workplacestructure**。
- [`.cursor/rules/workplacestructure.mdc`](.cursor/rules/workplacestructure.mdc) 增 **`run_id` 字面值** 小节并指回 §3.1。

### 验证

- 通读 §3.1 与 workplacestructure 新增节：四条与 BUG 预期一致；样例 JSON 无需改字段即可与 §3.1(4) 兼容。

### 修复说明（有则填）

- 

### 验证（关闭前填）

- 相关 **spec/`prompts`、`bootstrap/README`、`webhook/操作手册`** 补段后复审；读者不再将 `bootstrap-sample-run` **单独**视为违规命名。

