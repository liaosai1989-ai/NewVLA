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
| BUG-001 | 可执行文件依赖应统一为 PATH+标准解析，需全仓审计历史旁路 | P2 | 已确认 | 2026-04-27 | `onboard/README.md`、`onboard/src/feishu_onboard/lark_cli.py`、`docs/superpowers/plans/2026-04-27-feishu-fetch-lark-cli-workspace-init-implementation-plan.md` | onboard 已 `which`；`feishu_fetch` 在 facade 调 `lark-cli`+`which`，根 `.env` 含 `LARK_CLI_COMMAND` 时加载即失败；**全仓**关单仍待 |
| BUG-002 | 入轨 `POST .../permissions/.../members?type=folder` 在联调子命令可成功时仍 400/失败，属表现差异需收敛 | P1 | 已关闭 | 2026-04-27 | `onboard/src/feishu_onboard/flow.py`、`onboard/src/feishu_onboard/feishu_client.py` | 关闭：根因为 `.env` 中委托人 `open_id` 抄录少一位 → 1063001；修正后加协作者成功 |
| BUG-003 | `lark-cli config show` 误传 `--json`，与 @larksuite/cli 1.0.19 不符，致校验子进程退出码 1 | P1 | 已修复 | 2026-04-27 | `onboard/src/feishu_onboard/lark_cli.py`、`feishu_fetch/src/feishu_fetch/facade.py` | 改为 `config show`；`onboard`/`feishu_fetch` 单测与真机入轨可验 |

## 正文记录

> 按 `ID` 升序，标题为 `## BUG-XXX 一句话摘要`。

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

