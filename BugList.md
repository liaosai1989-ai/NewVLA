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
| BUG-004 | `feishu-onboard` 与 webhook 对同一路线双重登记 `qa_rule_file`/`dataset_id`，v1 运行时只消费 JSON 侧字段，易与根 `.env` 展示脱节 | P2 | 已确认 | 2026-04-27 | `webhook/操作手册.md` 第四步、`onboard/flow.py` | 真源约定冲突见 **BUG-005**；绕过：两处手工对齐 |
| BUG-005 | webhook 以 `FOLDER_ROUTES_FILE` JSON 为 folder 路由运行时来源，违反本仓「根 `.env` 唯一真源」约定（与 onboard / 其余模块不一致） | P1 | 已确认 | 2026-04-27 | `.cursor/rules/env.mdc`、`webhook/src/webhook_cursor_executor/settings.py`、`docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` | 修复方向：路由从 `.env` 的 `FEISHU_FOLDER_*` + 索引键解析；JSON 仅示例或派生产物 |
| BUG-006 | `feishu-onboard` 建应用文件夹后**未**调用飞书「夹级事件订阅」OpenAPI，缺 `file.created_in_folder_v1` 等前提，与同应用下能稳定收 `drive.file.edit_v1` 的栈（如含 subscribe 流程）表现不一致 | P1 | 已修复 | 2026-04-27 | `onboard/.../feishu_client.py` `subscribe_folder_file_created`、`flow.py` 建夹/已有 token 后协作者前调用 | 补订后同参考脚本；**勿**在 onboard 里枚举旧 docx；线上飞书需待验证 |

## 正文记录

> 按 `ID` 升序，标题为 `## BUG-XXX 一句话摘要`。

## BUG-006 `feishu-onboard` 建应用文件夹后未调飞书 OpenAPI「夹级 subscribe」（`file.created_in_folder_v1` 前提），与同应用能推编辑事件的栈不一致

- 发现时间：2026-04-27
- 当前状态：已修复
- 严重级别：P1
- 环境/复现：同一飞书应用、同租户；两个云文件夹分别由 **`feishu-onboard`（本仓）** 与 **含 subscribe 的管线（如 `VDBP-library-Automation`）** 建夹/入轨；仅对「经 onboard 的夹」在开放平台 **事件/投递** 中长期无或不稳定 **`drive.file.edit_v1`**，另一只夹可正常推。
- 现象：起初易误判为「路由 / webhook / 两夹元数据」问题；**对问题夹补** `POST https://open.feishu.cn/open-apis/drive/v1/files/{folder_token}/subscribe` 且 `file_type=folder`、`event_type=file.created_in_folder_v1`（并确保开发者后台已添加对应事件 type）后，**推送恢复**，可反证非「本机 webhook 不接收该夹」这一层单点。
- 预期：经 onboard 新建的应用文件夹，与同仓库其他入轨产品一致，在飞书侧具备 **订阅云文档 / 夹事件** 所需 OpenAPI 步骤（[订阅云文档事件](https://open.feishu.cn/document/server-docs/docs/drive-v1/event/subscribe)）；**不**在维护脚本中硬编码**枚举夹内所有现有 docx 并逐个 subscribe**（动态新增文档应靠 **`file.created_in_folder` → webhook/worker 内对 new `file_token` 调 `docx` subscribe** 等链路上的实现）。
- 根因（已定位）：`onboard` 的 `FeishuOnboardClient` / `flow.run_onboard` 在 **`create_folder`、加协作者** 后 **无** 上述「夹级 subscribe」调用；[对比] `VDBP-library-Automation` 的 `vla/feishu/client.subscribe_folder_file_created` 等。
- 相关链接：上文总表；`webhook/scripts/subscribe_byvwf_tds.py`（**仅**夹级 subscribe 的参考调用，**非**长期枚举 doc）；根 `.env` 中 `FEISHU_APP_*`；飞书《文件夹下文件创建》事件体含 `folder_token` 等（与 `drive.file.edit_v1` 无 `folder_token` 行为不同，webhook 侧已另有列目录/ingest 逻辑）。

### 修复说明（有则填）

- `FeishuOnboardClient.subscribe_folder_file_created`：`POST .../drive/v1/files/{token}/subscribe?file_type=folder&event_type=file.created_in_folder_v1`（与 `webhook/scripts/subscribe_byvwf_tds.py` 一致）。`run_onboard` 在取得 `folder_token`（新建或复用已有 route）后、**`add_folder_user_collaborator` 前** 调用；失败走既有 `FeishuApiError` 路径，不静默。未做「枚举夹内旧 docx」；docx 级 subscribe 仍属 webhook/worker 链路。

### 验证（关闭前填）

- `onboard` 下 `python -m pytest tests/` 全绿（本机 `.venv`）。生产租户建议再跑一次入轨或对手动 token 调 subscribe 在开放平台看投递。
- 文档：已同步 `docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md`（修订说明）、`docs/superpowers/plans/2026-04-27-feishu-app-folder-onboard-implementation-plan.md`（修订说明）、`onboard/README.md` / `onboard/操作手册.md`、`webhook/操作手册.md`、`webhook/阶段性验收手册.md`、根 `AGENTS.md`。

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
- 当前状态：已确认
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

- 

### 验证（关闭前填）

- 

## BUG-005 webhook 以 `FOLDER_ROUTES_FILE` JSON 为 folder 路由运行时来源，违反本仓「根 `.env` 唯一真源」约定

- 发现时间：2026-04-27
- 当前状态：已确认
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

- 

### 验证（关闭前填）

- 

