# Nice To Have

## 填报模板

> 用途：记录本仓库待优化功能点。
> 填写顺序：先补总表，再补正文。
> 适用对象：后续所有需要登记待优化点的 agent。

### 填写规则

- 新增待优化点时，先在 `待优化点总表` 新增一行，再在 `正文记录` 新增对应条目。
- `ID` 使用递增格式：`NTH-001`、`NTH-002`、`NTH-003`。
- `优先级` 统一使用：`P0`、`P1`、`P2`、`P3`。
- `状态` 统一使用：`待评估`、`规划中`、`开发中`、`已实现`、`已取消`。
- `spec 索引`、`plan 索引` 填对应文档路径；没有时填 `-`。
- 每次 plan 落地后，必须同步更新总表中的 `状态`、`spec 索引`、`plan 索引`，并在正文补充变更说明。
- 已实现的优化点不要删除，保留记录，状态改为 `已实现`。

### 正文条目模板

```md
## NTH-XXX 功能点标题

- 提出时间：
- 当前状态：
- 优先级：
- 背景/问题：
- 目标：
- 预期收益：
- 影响范围：
- spec 索引：
- plan 索引：
- 备注：

### 方案草案

- 

### 验收标准

- 
```

## 待优化点总表

| ID | 功能点 | 优先级 | 状态 | 提出时间 | spec 索引 | plan 索引 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NTH-001 | 重构 Dify 上传模块 | P1 | 已实现 | 2026-04-26 | `docs/superpowers/specs/2026-04-26-dify-upload-rebuild-design.md` | `docs/superpowers/plans/2026-04-26-dify-upload-rebuild-implementation-plan.md` | 已按 plan 完成纯 CSV 上传模块重建 |
| NTH-002 | webhook 补齐 Dify 目标配置合同 | P1 | 已实现 | 2026-04-26 | `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` | `docs/superpowers/plans/2026-04-26-root-env-and-dify-target-contract-implementation-plan.md` | 主路径：`task_context` 含 `dify_target_key`+`dataset_id`；`DIFY_TARGET_<KEY>_API_BASE`/`API_KEY` 等工作区根 `.env` 静态组由 `dify_upload.resolve_dify_target` 消费；legacy `FOLDER_ROUTES_FILE` 仍见 `load_routing_config` 回退 |
| NTH-003 | RQ 并发多个 Cursor CLI 的设计与实现优化 | P1 | 待评估 | 2026-04-26 | `docs/superpowers/specs/2026-04-26-webhook-cursor-executor-design.md` | - | 当前 spec 已覆盖基础并发语义，后续需单独优化稳定性与实现细节 |
| NTH-004 | 根目录 .env 与各模块配置消费合同收口 | P1 | 已出 spec | 2026-04-26 | `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` | - | 已明确各模块直接消费根 `.env` 各自分组，LLM 不注入基础设施配置，legacy Feishu 维持兼容保留 |
| NTH-005 | 飞书文件夹-Dify 知识库-QA 合同一对一映射收口 | P1 | 已实现 | 2026-04-26 | `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` | `docs/superpowers/plans/2026-04-26-root-env-and-dify-target-contract-implementation-plan.md` | 主路径：每条路由含 `folder_token`+`qa_rule_file`+`dataset_id`+`dify_target_key`；`task_context`/prompt 显式注入、禁猜。代码未 forbid 重复 token（先匹配先赢）；无 `FEISHU_FOLDER_ROUTE_KEYS` 可走 legacy JSON（BUG-005） |
| NTH-006 | 飞书 App 文件夹创建与权限初始化工具 | P1 | 已实现 | 2026-04-26 | `docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md` | `docs/superpowers/plans/2026-04-27-feishu-app-folder-onboard-implementation-plan.md` | `onboard/`：`feishu-onboard` 交互主流程 + **`verify-delegate`**；建夹后 **夹级 subscribe**（`file.created_in_folder_v1`）、**permissions/members** 加委托人（`FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID`）、两阶段 `.env`、`lark-cli config init`（`--app-secret-stdin`）；`--force-new-folder` / `--version`；`qa_rule_file` 可 `rules/` 或 **`prompts/rules/`**；非 editable 须 **`FEISHU_ONBOARD_REPO_ROOT`**；维护仓根 `.env` 与执行工作区交接见 **`bootstrap/README.md`**；细则 **`onboard/README.md`** |
| NTH-007 | 管线执行工作区物理目录初始化（与入轨解耦） | P2 | 待评估 | 2026-04-27 | `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`（相关；物化布局） | `docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md`（**`materialize-workspace`**） | **目录物化 + 任务 cwd 主路径已落地**（NTH-008）：`bootstrap materialize-workspace` 落 `{WORKSPACE}/.env`、`rules/`、`runtime/webhook/` 等；`webhook` `pipeline_workspace.path` 取根 `.env` 中 **`VLA_WORKSPACE_ROOT`**（未设则 `.env` 所在目录）→ snapshot → **`launch_cursor_agent(cwd=...)`** 与 **`.cursor_task/`** 同根；`ExecutorSettings` 找 `.env` 靠包路径上移，**不**用进程环境抢配置路径。`feishu_fetch`：`cwd` 下 `.env` 或 **`FEISHU_FETCH_ENV_FILE`**。**残留：** 运维误用维护仓 `.env` 且未写 `VLA_WORKSPACE_ROOT` 时路径仍回退维护仓；手册「项目根」与维护仓示例易混读；可选启动期硬校验、用语统一 — 无本条独立 spec |
| NTH-008 | bootstrap 收尾：内嵌 runtime、废 junction、`doctor` 后探活与可选服务脚本 | P1 | 已实现 | 2026-04-28 | `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`（主）；`docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md`（**§3.4** 待 **Task 10** 对齐） | `docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md`（主）；`docs/superpowers/plans/2026-04-28-production-bootstrap-deployment-implementation-plan.md`（旧版 junction §，**Task 10** 废止） | 内嵌 runtime / **`bootstrap probe`** 定型：**`doctor`** → **`probe --no-http`**；服务起后全量 **`probe`**（**`WEBHOOK_PROBE_BASE` + `/health`**）；**§10 / production-bootstrap §3.4** **未**并入本条目 closure；演进见 **NTH-009**（含原 **NTH-012**） |
| NTH-009 | 工作区 `materialize`/runtime 演进：必要树精简 + prompts/runtime 增量同步（免每次全量 bootstrap） | P2 | 待评估 | 2026-04-28 | - | - | **A（原 NTH-009）：** **`workspace-embedded-runtime-design.md` §5**，无 spec/plan 前不禁增量同步。**B（并入原 NTH-012）：** 物化时排除 **`tests/`**、缓存、维护侧一次性脚本等，与 **`doctor`/editable** 路径一致。**总表不再有 NTH-012 行** |
| NTH-010 | `bootstrap interactive-setup` 人机链串联（编排后续可复用 CLI） | P3 | 待评估 | 2026-04-28 | - | - | 接受工具分段复用；缺**同一交互流内**顺序编排，与 **NTH-006**/**NTH-008** 相邻 |
| NTH-011 | 工作区 `doctor`：pipeline 包须落工作区（混装克隆 / wheel 顶 editable） | P2 | 待评估 | 2026-04-28 | `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`（§4.1、§6、`doctor` plan A.3） | - | **现象 B 主力已缓解：** `bootstrap/install_workspace_editables.py` 固定顺序且在 **`runtime/webhook` 装完后**再 **`pip install -e` 工作区 `vla_env_contract`** 重钉 editable。**仍存：** `_workspace_import_paths_ok` 失败时仅泛化一条 ERROR；跳过该命令、克隆根混装、脏 `site-packages` 仍踩雷。与 **BUG-007** 不同根因；见正文 |

> **ID 提示：** **NTH-012** 已并入 **NTH-009**，不再单独占表/正文；下文仅 **## NTH-009**。

## 正文记录

> 按 `ID` 顺序逐条登记，标题格式保持为 `## NTH-XXX 功能点标题`。

## NTH-001 重构 Dify 上传模块

- 提出时间：2026-04-26
- 当前状态：已实现
- 优先级：P1
- 背景/问题：
  - 现有 `old_code/dify_upload` 只是最小参考实现。
  - 旧代码将配置、HTTP、业务判断、返回结构混在一起。
  - 旧代码使用单一 `RuntimeError`，不利于上游分类处理。
  - 当前仓库的新架构已明确：路由在 `webhook`，上传模块应收窄为纯上传边界。
- 目标：
  - 在 `c:\WorkPlace\NewVLA\dify_upload` 下建设新的上传模块。
  - 只接收显式 Dify 目标配置，不承担路由职责。
  - 输出结构化结果，并提供清晰异常模型。
- 预期收益：
  - 与 `webhook` 边界清晰，避免职责重叠。
  - 方便当前管线复用，也方便后续维护。
  - 失败路径更易于记录、告警和排障。
- 影响范围：
  - `dify_upload/`
  - 可能的调用方适配代码
- spec 索引：
  - `docs/superpowers/specs/2026-04-26-dify-upload-rebuild-design.md`
- plan 索引：
  - `docs/superpowers/plans/2026-04-26-dify-upload-rebuild-implementation-plan.md`
- 备注：
  - 旧代码只作参考，不直接搬运。
  - 2026-04-26 已按 spec 与 plan 完成落地，现模块收敛为纯 CSV 上传边界，提供结构化返回与清晰异常模型。

### 方案草案

- 新模块分为配置模型、HTTP 封装、上传主流程、返回模型、异常模型五层。
- 路由逻辑继续保留在 `webhook`，不回流到 `dify_upload`。
- 第一版只支持当前需要的 CSV 上传能力。

### 验收标准

- 调用方可显式传入一套 Dify 目标配置完成上传。
- 成功时返回结构化结果。
- 失败时能区分配置错误、HTTP 错误、响应错误、业务错误、不完整成功。
- 模块不承担 `folder_token` 路由职责。

## NTH-002 webhook 补齐 Dify 目标配置合同

- 提出时间：2026-04-26
- 当前状态：已实现
- 优先级：P1
- 背景/问题：
  - 当前 webhook 相关设计里，运行时合同稳定覆盖的是 `dataset_id`。
  - 但后续调用 `dify_upload` 时，实际还需要 `api_base`、`api_key`。
  - 目前这两个字段的来源、存放位置、组装时机没有在 webhook 侧设计中明确。
- 目标：
  - 补齐 webhook 到上传模块之间的 Dify 目标配置合同。
  - 明确 `api_base`、`api_key` 由哪一层提供。
  - 明确它们是否进入运行时注入、工作区本地配置，或由中间适配层组装。
- 预期收益：
  - 避免 `webhook` 与 `dify_upload` 在输入合同上脱节。
  - 降低后续实现时的临时补丁与边界漂移。
  - 让运行时配置、静态配置、上传模块接口三者对齐。
- 影响范围：
  - `webhook` 设计文档
  - 运行时合同
  - `dify_upload` 调用适配层
- spec 索引：
  - `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md`
- plan 索引：
  - `docs/superpowers/plans/2026-04-26-root-env-and-dify-target-contract-implementation-plan.md`
- 备注：
  - 已与 `NTH-004` 合并收口。
  - 已确定 `dataset_id` 必须运行时显式传入，根 `.env` 不允许提供默认值。
  - **落地（主路径，2026-04-28 plan 文首；代码核对 2026-04-30）：** `webhook` 路由从根 `.env` 的 `FEISHU_FOLDER_*` 组写入 snapshot / `task_context.json` 的 `dataset_id` 与 `dify_target_key`；`dify_upload.resolve_dify_target` 从工作区根 `.env` 读 `DIFY_TARGET_<KEY>_API_BASE` / `API_KEY` 等并完成上传；`task_files` 提示禁止手拼密钥。未收口项：无 `FEISHU_FOLDER_ROUTE_KEYS` 时仍可走 legacy JSON（与真源仅 `.env` 的最终目标存 gap，见 `BugList` BUG-005）。

### 方案结论

- `dataset_id` 必须由运行时显式传入。
- `api_base`、`api_key` 由 `dify_upload` 自己从根 `.env` 读取。
- LLM / `task_context.json` 不注入 Dify 静态连接配置。

### 验收标准

- webhook 侧明确 `api_base`、`api_key` 不进入运行时合同。**（已满足）**
- `dify_upload` 的输入合同与 `dataset_id` 显式传入口径闭环。**（已满足）**
- 根 `.env` 不再承担默认 `dataset_id` 注入职责。**（已满足； per-route `FEISHU_FOLDER_*_DATASET_ID` 仍为映射真源，非默认值魔法键）**

## NTH-003 RQ 并发多个 Cursor CLI 的设计与实现优化

- 提出时间：2026-04-26
- 当前状态：已出 spec
- 优先级：P1
- 背景/问题：
  - 当前 webhook spec 已定义“多文档可并发、单文档尽量不并发”的基础语义。
  - 但 RQ 并发拉起多个 Cursor CLI 时，仍涉及实际并发度控制、失败路径、运行隔离、全局 Cursor 配置副作用等工程细节。
  - 当前 spec 更偏最小闭环，后续实现时仍需要单独优化并发稳定性与实现细节。
- 目标：
  - 细化 RQ 并发多个 Cursor CLI 的落地方案。
  - 明确并发启动、运行隔离、失败收敛、资源占用与配置副作用边界。
  - 在不破坏当前“最小可行设计”的前提下，补齐可实施的工程优化点。
- 预期收益：
  - 降低多个 Cursor CLI 并发运行时的相互干扰。
  - 提高任务调度稳定性与排障效率。
  - 为后续实现阶段减少临时补丁和边界漂移。
- 影响范围：
  - `webhook` 调度与执行器实现
  - Cursor CLI 启动与运行时隔离
  - 相关配置与运行目录策略
- spec 索引：
  - `docs/superpowers/specs/2026-04-26-webhook-cursor-executor-design.md`
- plan 索引：
  - -
- 备注：
  - 当前仅登记为待优化点，不改变现有 spec 的最小方案边界。

### 方案草案

- 方案一：继续沿用当前最小设计，只在实现阶段补齐必要的并发保护与失败处理。
- 方案二：在执行器层增加更细的并发度与资源隔离控制，但不引入重型编排系统。
- 方案三：将部分高风险并发能力下沉为后续独立优化项，避免 v1 过度设计。

### 验收标准

- 明确 RQ 并发多个 Cursor CLI 的实现边界与风险点。
- 并发运行时不破坏现有 `run_id` 目录隔离与单文档互斥语义。
- 不因并发补丁引入明显过度设计或额外系统复杂度。

## NTH-004 根目录 .env 与各模块配置消费合同收口

- 提出时间：2026-04-26
- 当前状态：已出 spec
- 优先级：P1
- 背景/问题：
  - 当前仓库根目录 `.env` 已完成按模块分组整理，覆盖了 `webhook`、`dify_upload`、`feishu_fetch` 以及用户要求保留的 legacy Feishu 集成配置。
  - 但目前真正直接从根 `.env` 读取的主要还是 `webhook`。
  - `dify_upload` 当前吃的是显式传入的结构化目标配置，`feishu_fetch` 计划中也还未正式落地到根配置消费层。
  - 这会导致“配置已经集中整理”和“代码实际如何消费这些配置”之间仍有缝。
- 目标：
  - 明确哪些配置必须由模块直接从根 `.env` 读取。
  - 明确哪些配置只应由适配层组装后传入模块。
  - 明确 legacy Feishu 配置是长期保留、迁移过渡，还是后续待下线。
- 预期收益：
  - 避免根 `.env` 继续变成“只堆键名、不清楚谁在用”的杂物间。
  - 降低后续实现 `dify_upload`、`feishu_fetch` 时的临时猜测和重复改配置。
  - 让配置边界与模块边界一致，后续排障更直接。
- 影响范围：
  - 仓库根 `.env`
  - `webhook/`
  - `dify_upload/`
  - `feishu_fetch/`
  - 相关 README / spec / plan 文档
- spec 索引：
  - `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md`
- plan 索引：
  - -
- 备注：
  - 已与 `NTH-002` 合并收口。
  - 已明确各模块直接消费根 `.env` 各自配置分组，不新增独立 resolver 层。

### 方案结论

- `webhook`、`dify_upload`、`feishu_fetch` 都直接读取根 `.env` 中属于自己的配置分组。
- LLM 只传业务运行时参数，不传 `api_key`、`app_secret`、命令路径、默认超时这类静态配置。
- legacy Feishu 配置继续保留在根 `.env`，但不扩大主链路默认依赖。

### 验收标准

- 能明确说清每一组配置由哪个模块直接读取。
- `webhook`、`dify_upload`、`feishu_fetch` 的配置来源不再互相打架。
- legacy Feishu 配置的定位清晰，不再长期处于“先留着但没人负责”的状态。

## NTH-005 飞书文件夹-Dify 知识库-QA 合同一对一映射收口

- 提出时间：2026-04-26
- 当前状态：已实现
- 优先级：P1
- 背景/问题：
  - 当前系统已经有 `folder_token` 路由语义，也有 `dataset_id` 和 QA 规则文件注入语义。
  - 但“飞书文件夹、Dify 知识库、QA 合同”三者的一对一绑定关系还没有单独收口成稳定合同。
  - 如果后续只是零散地加配置，容易退化成运行时猜测、隐式回退或映射漂移。
- 目标：
  - 明确不同飞书文件夹必须触发不同业务合同。
  - 明确每个飞书文件夹稳定绑定一套 Dify 知识库和一份 QA 合同。
  - 明确映射结果由上游显式注入，Agent 不负责自行推断目标合同。
- 预期收益：
  - 让业务分流规则和上传目标保持稳定，不因实现细节临时漂移。
  - 降低新增文件夹或新增业务线时的配置歧义。
  - 让 `webhook`、运行时上下文、工作区规则资产三者边界更清晰。
- 影响范围：
  - `webhook/` 路由配置与任务注入
  - `task_context.json` 合同
  - `rules/` 或对应 QA 合同模板资产
  - Dify 数据集目标配置
- spec 索引：
  - `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md`
- plan 索引：
  - `docs/superpowers/plans/2026-04-26-root-env-and-dify-target-contract-implementation-plan.md`
- 备注：
  - 已与 `NTH-002`、`NTH-004` 一并收口。
  - 核心约束是一对一绑定和显式注入，不接受运行时猜测。
  - **落地（主路径，2026-04-28 plan 文首；代码核对 2026-04-30）：** `vla_env_contract.feishu_folder_group_keys` 五键成套；`webhook` `FolderRoute` + `resolve_folder_route`；snapshot / `task_context.json` / `task_files` 对齐。`prompts`/执行手册侧亦约定跟 `qa_rule_file`。**缺口：** 配置的 `folder_token` 若在多条 route 重复，实现为「首个匹配」，无启动期唯一性校验；真源完全弃 JSON 见 BUG-005。

### 方案结论

- 由根 `.env` 的 `FEISHU_FOLDER_<KEY>_` 业务组（及过渡期的 `FOLDER_ROUTES_FILE` JSON）提供映射；`webhook` 解析后命中单条 `FolderRoute`，显式注入 `folder_token`、`dify_target_key`、`dataset_id`、`qa_rule_file`。
- Agent 不负责推断 Dify 实例、目标知识库或 QA 合同。
- 根 `.env` 同时承载：① 按 route 的飞书夹↔业务合同映射（五键组）；② `DIFY_TARGET_<KEY>_` 静态 Dify 实例组（由 `dify_upload` 等消费，与 `NTH-002` 一致）。

### 验收标准

- 能明确说清每个飞书文件夹对应哪一套 Dify 实例、哪一个知识库和哪一份 QA 合同。**（主路径已满足：同条 `FolderRoute` 绑定 `dify_target_key`+`dataset_id`+`qa_rule_file`；Dify 连接细节见 `DIFY_TARGET_*` 组。）**
- 不同飞书文件夹触发的业务合同不再依赖 Agent 推断。**（已满足：`task_files` 禁猜路由。）**
- 新增或调整映射时，只需要改一处主配置，不会出现多处定义互相打架。**（已满足：首选根 `.env` 单真源；legacy JSON 为回退，与「一处」目标仍差一口，见 BUG-005。）**

## NTH-006 飞书 App 文件夹创建与权限初始化工具

- 提出时间：2026-04-26
- 当前状态：已实现
- 优先级：P1
- 背景/问题：
  - 按飞书规则，本仓库业务链路使用的目标文件夹必须是 App 文件夹，不能直接使用用户个人文件夹。
  - 当前仓库缺少一套辅助工具，去自动创建符合要求的飞书文件夹并完成基础权限初始化。
  - 现有配置链路里，往往要先拿到飞书文件夹 token，才能继续把映射关系写回根 `.env`。
- 目标：
  - 提供一个基于飞书 OpenAPI 和飞书 App ID 的辅助工具。
  - 该工具能自动创建对应的 App 文件夹；为指定委托人加文件夹协作者并完成夹级订阅（使 `file.created_in_folder_v1` 等事件链可用，与 webhook 侧衔接）。
  - 创建成功后，能拿到目标 `folder_token` 并两阶段回写到目标根 `.env`，供后续映射配置继续使用。
- 预期收益：
  - 避免人工先去飞书侧建目录、再手抄 token，减少配置错误。
  - 保证本仓库使用的文件夹类型符合飞书约束，不会混入用户个人文件夹。
  - 让“创建文件夹 -> 拿 token -> 写配置”形成可重复执行的标准化链路。
- 影响范围：
  - 飞书 OpenAPI 调用封装
  - 文件夹初始化辅助工具
  - 仓库根 `.env` 回写逻辑
  - 与 `folder_token` 相关的映射配置流程
- spec 索引：
  - `docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md`
- plan 索引：
  - `docs/superpowers/plans/2026-04-27-feishu-app-folder-onboard-implementation-plan.md`
- 备注：
  - 本条是初始化辅助工具，不改变现有 `webhook` 与 Agent 的主链路边界。
  - 重点是把 App 文件夹入轨（建夹、订阅、协作者、`.env`、`lark-cli`）收口成可执行工具，而不是靠人工步骤维持。
  - **实现现状（对齐 `onboard/README.md` / 源码；2026-04-30 总表备注同步）：**
    - **包与入口：** 根目录 `onboard/`，`pip install -e .[test]`；控制台 **`feishu-onboard`**；子命令 **`feishu-onboard verify-delegate`**（只测建夹 + 协作者，不做 subscribe）。
    - **流程：** 校验输入与 `DIFY_TARGET_<KEY>_` 组、本地 `qa_rule_file` → 按需建夹（默认租户云空间根，`parent_folder_token` 可填）→ **`subscribe_folder_file_created`**（夹级 `file.created_in_folder_v1`）→ **`add_folder_user_collaborator`**（须根 `.env` **`FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID`**）→ 仓根 **`lark-cli config init --app-secret-stdin`** 与校验 → 仅协作者与 lark 均成功时 **阶段 B** 写 **`FEISHU_FOLDER_ROUTE_KEYS`**。
    - **CLI 旗标：** **`--force-new-folder`**（已有 `FEISHU_FOLDER_<KEY>_TOKEN` 仍新建夹）；**`--version`**（确认加载包路径）。
    - **路径合同：** `qa_rule_file` 仅相对路径，须以 **`rules/`** 或 **`prompts/rules/`** 开头（维护仓可指模板）；非 editable 安装须 **`FEISHU_ONBOARD_REPO_ROOT`** 指管线仓根。
    - **出口码：** **0** 全成；**2** 校验/飞书硬错/路由冲突等；**3** 部分完成（常见协作者或 lark 未过，阶段 A 可能已写，阶段 B 未写）；**1** 中断或未捕异常。
    - **运维边界：** 工具默认读写的是**管线维护仓根** `.env`；**运行合同真源为物化后的执行工作区根 `.env`**，须按 **`bootstrap/README.md`** 合并/复制交接，勿混为一谈。
  - `pytest` 覆盖核心路径；与「仅 JSON 路由、无根 `.env` 五键」类缺口属 **BUG-005 / NTH-004** 范畴，不在本条工具内闭环。

### 方案草案

- 已采纳 plan：独立子包于 `onboard/`，不并入 webhook 运行时；按 spec 两阶段写（阶段 A 业务分组、阶段 B `FEISHU_FOLDER_ROUTE_KEYS` 门禁于 **协作者成功 + `lark-cli` 校验成功** 之后）。
- 实现已含 **夹级 subscribe**（与 webhook 文档/脚本侧「建夹后须 subscribe」口径一致），非仅「公开可见」一语可概括。
- 原方案中批量初始化、自 `webhook` 派生 `folder_routes.example.json` 等仍为 plan 声明的非本条目必达项。

### 验收标准

- 能通过飞书 OpenAPI 基于 App 身份创建出可用于本仓库的 App 文件夹。**（已实现；见 `feishu_client` / `flow`。）**
- 建夹后对目标夹完成 **夹级 subscribe**（`file.created_in_folder_v1`），并为委托人 **POST permissions/members** 加协作者；失败语义与 **exit 2 / 3**、阶段 B 门禁一致（见 README）。**（已实现。）**
- 工具能拿到正确的 `folder_token` 并稳定两阶段回写到根 `.env` 指定配置项（与 feishu-app-folder onboard spec 键名一致，含续跑/冲突与 **`--force-new-folder`** 语义，以 `onboard` 内单测与 README 为准）。**（已实现。）**

## NTH-007 管线执行工作区物理目录初始化（与入轨解耦）

- 提出时间：2026-04-27
- 当前状态：待评估
- 优先级：P2
- 背景/问题：
  - **生产现实（须默认成立）：** 实际跑 webhook/RQ/Cursor 管线任务时，**不应**以「本维护仓 Git 工作副本」冒充执行根；任务应在**单独物化目录**（执行工作区）。维护仓只负责源码与模板。
  - **`feishu-onboard`（NTH-006）** 写**其认定的仓根** `.env`、在同目录跑 `lark-cli`；**不**替代 **bootstrap 物化**一整棵执行区树；与根 `AGENTS.md`「维护仓 ≠ 单次任务工作区」一致。
  - **原「断链」焦点：** 文档/验收常把「项目根」说成维护仓路径，与 RQ/Cursor 真实 **`pipeline_workspace.path`** 不符；`feishu_fetch` 依赖 **工作区根 `.env` + 子进程 cwd**（或通过 **`FEISHU_FETCH_ENV_FILE`** 指到该 `.env`）。
- 目标：
  - （历史）明确入轨与执行区初始化分工；执行区目录树、与 `.env` / lark 对齐方式。
  - 文档层：**项目根 / 仓库根 / cwd** 必须能区分**维护仓**与**执行工作区**。
  - 可选：启动期机检、手册用语扫尾（不重复 NTH-006 建夹能力）。
- 预期收益：
  - 减少「以为 onboard 会建工作区」或「维护仓即生产根」的配置事故。
  - 物理隔离时搭盘方式与代码行为一致。
- 影响范围：
  - `bootstrap/`、`webhook` 路由与工作区路径、`feishu_fetch`、各 `README`/操作手册措辞
- spec 索引：
  - （本条无独立 spec；执行区物化布局相关）`docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`
- plan 索引：
  - （本条无独立 plan；`materialize-workspace`/`doctor`/`probe` 相关）`docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md`
- 备注：
  - **代码现状（2026-04-30 核对）：**
    - **`bootstrap materialize-workspace`**：`validate_workspace_root_path` 防工作区等于 clone 根误配；拷贝 `AGENTS.md`、`prompts`→`rules/`、`tools/`、`vla_env_contract`、**`runtime/webhook/`** 等到 `{WORKSPACE_ROOT}`（见 `bootstrap/materialize.py`）。
    - **`webhook`：** `_routing_from_env` 中 **`VLA_WORKSPACE_ROOT`** 优先，否则 **已加载根 `.env` 的父目录** 为 `pipeline_workspace.path`；snapshot 写入 **`workspace_path`**；**`scheduler.launch_cursor_agent(cwd=snapshot.workspace_path)`**，**`write_task_bundle`** 同路径 — 与执行区根对齐。
    - **`ExecutorSettings._env_file()`：** 沿 **webhook 包安装路径**向上找 `.env`，**不**读取进程 **`VLA_WORKSPACE_ROOT`** 切换配置文件位置（避免与「双机双 clone」混淆）；物化安装下通常解析到 **工作区根 `.env`**。
    - **`feishu_fetch`：** **`FEISHU_FETCH_ENV_FILE`** 或 **`cwd`** 下 `.env`；子进程 **`cwd=workspace_root`**（`.env` 父目录）。
  - **仍为「待评估」原因：** 无独立收口 spec/plan；**运维若从维护仓起服务且 `.env`/键未指向工作区**，仍会落在维护仓路径 — 属 **配置纪律 + 文档警示**，可加可选硬校验并入本条或 BUG 单；`feishu_fetch/人工验收操作手册.md` 等 「项目根」示例需读者自行映射到执行区（或使用 `FEISHU_FETCH_ENV_FILE`）。
  - 不反向要求改动已落地的 NTH-006 行为，除非经评审合并需求。
  - 2026-04-27：用户补充 — 生产任务目录 = 专用执行工作区；与「断链」同一主题，归入 NTH-007。

### 方案草案

- **方案三（编排/物化）已主路径生效：** **`bootstrap interactive-setup` / `materialize-workspace`** + NTH-008 内嵌 runtime；生产启动前设 **`VLA_WORKSPACE_ROOT`** 与工作区根一致（见 **`webhook/操作手册.md`**）。
- **方案一（文档）部分落实：** `操作手册`、`onboard/README` 已写维护仓 vs 执行区；全仓「项目根」用语仍可扫。
- **方案二**（`feishu-onboard workspace init` 等）：仍未做；是否需要取决于是否坚持「仅 bootstrap 物化」单入口。

### 验收标准

- 操作者能理解：**入轨成功 ≠ bootstrap 已完成**；生产任务根 = **`pipeline_workspace.path`**（通常即工作区根），与维护仓分立。
- 操作者能理解：维护仓跑的 **onboard** 与 **物化后的工作区 `.env`/lark** 须按 **`bootstrap/README.md`** / onboard README **交接对齐**。
- **`feishu_fetch`：** 在非工作区 `cwd` 调试时知晓 **`FEISHU_FETCH_ENV_FILE`** 或使用工作区根为 cwd（见 **`feishu_fetch/README.md`**）。
- （可选）日后若加固：启动时对 **加载中的 `.env` 路径 vs `pipeline_workspace.path`** 做 WARNING/ERROR — 记入本条或新 BUG。

## NTH-008 bootstrap 收尾：内嵌 runtime、废 junction、`doctor` 后探活与可选服务脚本

- 提出时间：2026-04-28
- 当前状态：已实现
- 优先级：P1
- 背景/问题：
  - 当前 **`bootstrap doctor`** 已覆盖 Python 版本、PATH 工具、`markitdown`、四包可导入、工作区 `.env`、可选 Redis ping、路由 JSON 漂移 WARNING 等（见 plan Task 9）。
  - **缺口 A（探活）：** 投产前常还需确认 **合同配置完整性**（必填键是否存在/非占位）、**依赖服务真实可达**（不仅进程已起），以及可选的 **Dify API、飞书网关、RQ 队列** 等——与「本机 CLI/包存在」不同维度；若全靠人工对照 `操作手册`，易遗漏。
  - **缺口 B（内嵌 runtime）：** 物化若仍用 **junction** 把 **`tools/*`** 指回 **`{CLONE_ROOT}`**，或 **webhook** 只在克隆根启动，则 **7×24 运行**仍绑定克隆路径，与「克隆仅部署介质」不一致（见 **`docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`** 全文及 **§10** 代码删除要求）。
- 目标：
  - **探活：** 在 bootstrap **人机验收链末端**（`interactive-setup` 及/或独立子命令）增加 **「探活」环节**：在 **`doctor` 现有检查之后**（或与之分层），汇总 **配置探针 + 服务探针**，退出码与输出可区分「硬失败 / 软警告 / 跳过项未配置」。探活范围可分级（例如 P0：`.env` 键门禁 + Redis；P1：HTTP ping 外联，需显式开关防误触生产）。
  - **内嵌 runtime：** 按 **`2026-04-28-workspace-embedded-runtime-design.md`** 物化 **`runtime/webhook`** + **`tools/*`** 实拷贝；**§10** 从 **`bootstrap/`** 移除 junction 相关实现、CLI、单测；README、验收脚本、**production bootstrap** §3.4 同步。
  - **可选：** **Windows 服务**（NSSM/WinSW）安装脚本由 bootstrap **生成**；`materialize` 末尾自动注册服务 **非** P0，可分期写入同一 plan。
- 预期收益：
  - 目录与代码 **不**再依赖克隆路径常驻；**外联可达性**在签字前可机检。
- 影响范围：
  - **`bootstrap/`**（`materialize`、`doctor`、新探活模块、`cli`、`interactive_setup`、`junction` 删除、tests）
  - **`bootstrap/README.md`**、**`bootstrap/scripts/*.ps1`**、**`webhook/操作手册.md`**
  - **`docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md`** §3.4
- spec 索引：
  - `docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md`
  - `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`
- plan 索引：**主线** **`docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md`**（物化、`doctor`、**`bootstrap probe` 定型**、`Task 10` 延后修订旧 production-bootstrap plan/spec）；legacy **`docs/superpowers/plans/2026-04-28-production-bootstrap-deployment-implementation-plan.md`**（junction §）待 **`Task 10`** 废止
- 备注：
  - 用户曾登记「bootstrap 最后加探活」；**2026-04-28** 与用户对齐：**不**另立 NTH，**内嵌 runtime / 废 junction** 与 **探活** 统归本条。
  - **2026-04-28：** **主路径已落地**；**`bootstrap probe`** 为签字链定型产物（**`--no-http`** 与全量含 **`GET {WEBHOOK_PROBE_BASE}/health`**，见 workspace implementation plan **附录 B** 与 **`docs/superpowers/samples/pipeline-workspace-root.env.example`**）。
  - **`docedit` / `plan-landed-renew`**：plan **落地后** **renew** **`prompts/AGENTS.txt`**、根 **`AGENTS.md`** 与内嵌布局一致。
  - **版本迭代：** 与 **`workspace-embedded-runtime-design.md` §5** 一致——**每次**新版本 **完整重新 bootstrap**；**不**在本条 plan 做「增量同步 runtime」。演进需求见 **NTH-009**（已合并原 **NTH-012** 物化精简面）。

### 方案草案

- 探活：候选矩阵 `REDIS_URL`、`FOLDER_ROUTES_FILE` 可读性、`DIFY_TARGET_*` 组完整性、`WEBHOOK_PROBE_BASE` + **`GET /health`**（全量）；`interactive-setup` 末尾：**`doctor`** → **`bootstrap probe --no-http`**；生产起服务后再 **`bootstrap probe`**（无 **`--no-http`**）；CI/Merge：`SkipProbe` / `-SkipProbeHttp` 见 **`2026-04-28-workspace-embedded-runtime-implementation-plan.md`**。
- 内嵌 runtime：以 **`workspace-embedded-runtime-design.md`** §3 + §10 为 PR 清单；`doctor` 增加实目录/禁联接克隆校验（§6）。
- CI：外联探针默认跳过或 `SkipProbe` 同级开关。

### 验收标准

- **代码：** **`tools/*`** 路径 **无** `ensure_junction`；单测覆盖拷贝物化；**§8** 整机与文档一致。
- **探活：** 文档写明与人机签字关系；无密钥不强行打生产 API。
- 与现有 Task 14 闸门脚本兼容或可追加可选一步。

## NTH-009 工作区 `materialize`/runtime 演进：必要树精简 + prompts/runtime 增量同步（免每次全量 bootstrap）

- 提出时间：2026-04-28（**B 面**原 **NTH-012** 提出 2026-04-29，已并入本条）
- 当前状态：待评估
- 优先级：P2（合并后取 **P2**：物化精简与运维成本更紧迫；**A 面**增量同步仍为 **远期**，无 spec 前不做）
- 背景/问题：
  - **A 面 — 增量同步（原 NTH-009）：** **`2026-04-28-workspace-embedded-runtime-design.md` §5** 明确 **本轮** **不**做在线/增量升级：发版依赖 **全量重新 bootstrap**。**远期** 可能希望在 **`{WORKSPACE_ROOT}`** 已存在时，仅用 **覆盖拷贝 `runtime/webhook`、`tools/*`** + **`pip install -e .`** + **重启服务**（及/或与 **`prompts` → `AGENTS.md`/`rules/`** 收成 **单一子命令**），缩短小版本/热修路径。
  - **B 面 — 物化必要树（原 NTH-012）：** 现 **`copy_materialize_subtree` / `materialize-workspace`** 从克隆**整树**拷入执行区，**`tests/`**、**`__pycache__`**、维护侧 **一次性排障/验证脚本** 等一并过去，执行区臃肿且易误导（非生产入口）。与 **NTH-008** 已落地的「能装能跑」不矛盾，属 **拷贝策略** 优化。
- 目标：
  - **A：** **待** 独立 **design spec + implementation plan** 后定：同步粒度、与 **工作区 `.env`** / 任务目录兼容、回滚与验收。
  - **B：** 物化 **白名单或忽略规则**：**仅**运行与 **`install-workspace-editables` / `doctor`** 所需源码与元数据（**`pyproject.toml`、`src/`**、包内非测资源等）；**默认不拷** **`tests/`**、**`.pytest_cache`**、明显 **dev-only** 脚本（名单落地时与克隆树校准）。
- 预期收益：
  - **A：** 减少全量停机与重复步骤（若安全可证）。
  - **B：** 工作区更小更清晰；降低误运行维护仓测试树的风险。
- 影响范围：
  - **`bootstrap/`**（`copy_trees` / **`materialize.py`**、`cli`、潜在新子命令）、**`bootstrap/README.md`**、**`workspace-embedded-runtime-design.md`** **§5**、必要时 **production-bootstrap** 文档「物化产物」描述。
- spec 索引：`-`（出稿后替换）
- plan 索引：`-`
- 备注：
  - **不**阻塞 **NTH-008**；**无** spec 前 **禁止**把 **A 面**当合同实现。
  - **B 面**须与 workspace-embedded-runtime：**工作区**仍能 **`pip install -e`** 与 import；若某包测试目录被 tooling 误依赖需单列例外。
  - **原 NTH-012** 总表与独立正文已撤销，统一以本条登记。

### 方案草案

- **B：** 扩展 **`materialize_copy_ignore`**（或等价）：`tests`、`__pycache__`、`.pytest_cache`、按需 `scripts/` 子集。**CI：** `test_materialize` 断言目标树 **无** `tests/` 或抽样 `webhook` **无** `tests/`。
- **A：** （空；待 spec 后补）

### 验收标准

- **B：** 干净物化后执行区 **无**（或文档声明的极少数例外下 **无**）克隆侧 **`tests/`**；**`doctor` + 生产起服务路径** 不受影响。
- **A：** （空；待 spec 后补）

## NTH-010 `bootstrap interactive-setup` 人机链串联（编排后续可复用 CLI）

- 提出时间：2026-04-28
- 当前状态：待评估
- 优先级：P3
- 背景/问题：
  - 已接受 **分段** 与 **复用既有工具**（`feishu-onboard`、`doctor`、`probe` 等）；**不顺**的是 **`interactive-setup` 仅在末尾打印提示**，未把「物化 → 可选入轨 → 自检 → 探活」收成 **一条人机链上的有序步骤**，易忘步、误以为「一条命令已全部完成」。
  - **机密、部署侧 `VLA_WORKSPACE_ROOT`、起 Redis/webhook 进程** 仍不宜假称全自动；合理范围是 **可脚本化/可子进程化的步骤** 在**同一会话**内 **显式串联**（含 **暂停等用户登录/填表**）。
- 目标：
  - 在 **`bootstrap interactive-setup`**（及/或 **`--continue`** 续跑）中 **编排**：例如在 **`materialize` + `install_workspace_editables` 之后**，可选 **`subprocess` 调用 `feishu-onboard`**（仍为交互 CLI）、失败即打断并返回码清晰；再继续 **`doctor`** / **`probe`** 等与 **NTH-008** 已定链一致。
  - 备选：**不改自动调用**，改为 **编号清单 + 可复制下一条命令**，降低心智负荷。
- 预期收益：
  - 运维/初始化 **单会话闭环感**；减少遗漏 **`feishu-onboard`** 或顺序错误。
- 影响范围：
  - **`bootstrap/src/bootstrap/interactive_setup.py`**、**`cli.py`**（新 flag 若有）、**`bootstrap/README.md`**、单测。
  - **`onboard/`** 无需改大包边界；仅调用约定（cwd、`VLA_WORKSPACE_ROOT`）需在正文/README 写清。
- spec 索引：`-`
- plan 索引：`-`
- 备注：
  - 与 **NTH-006**（`feishu-onboard` 能力）、**NTH-008**（`doctor`→`probe` 链）相邻；**不**重复登记内嵌 runtime 与探活本身。

### 方案草案

- **`--with-onboard`**：物化成功后 **`check_call` 本机 `feishu-onboard` 入口**（或 `python -m`），stdin/stdout 仍接用户终端；失败非 0 则 **`interactive-setup` 非 0**。
- 或 **交互问答**「是否现在运行入轨？」选 Y 再调起子进程。
- **明列不串联项**：密钥填表、进程管理，仅 README/输出中 **列硬边界**。

### 验收标准

- 有一条可复述的 **官方推荐顺序**（代码或文档一致）；新用户不必从多处拼流程。
- 可选 onboard 路径在 **Windows** 与 **POSIX** 下子进程退出码可区分失败/成功。
- 不将 **秘钥写入** 或 **冒充** 已完成 feishu 侧授权。

## NTH-011 工作区 `doctor`：pipeline 包须落工作区（混装克隆 / wheel 顶 editable）

- 提出时间：2026-04-28
- 当前状态：待评估
- 优先级：P2
- 背景/问题：
  - **`bootstrap doctor --workspace <WS>`** 要求 `feishu_fetch`、`dify_upload`、`webhook_cursor_executor`、`vla_env_contract` 的 **`importlib.util.find_spec` 解析路径**均落在 **`{WORKSPACE_ROOT}`** 下（plan A.3 / `doctor.py` **`_workspace_import_paths_ok`**）。
  - **现象 A：** 同一 **`py -3.12`** 曾在**维护仓克隆根**对 pipeline 包做过 **`pip install -e`**，运行 **`doctor`** 时仍解析到 **克隆路径** → **`pipeline packages must resolve under workspace root`**。
  - **现象 B：** `runtime/webhook` 的 **`pip install -e .`** 可能把 **`vla-env-contract`** **拉成 wheel** 落到 **`site-packages`**，**`find_spec` 结果** 偏离 **`{WS}/vla_env_contract`**。**代码已处理：** 见下「已实现」— 标准路径下 **不必**只靠人手「再补一次 `-e`」才发现。
  - 与 **BUG-007**（错误 **`cwd`** 下 `file:` 路径断裂、errno 2）**不同**：本条属 **解析落点**（仓外 / 非工作区 editable）与 **运维顺序**。
- 目标：
  - **已实现部分：** **`install-workspace-editables`** 减低现象 B。**仍希望：** **`doctor`** 失败时 **逐包**打出 **`spec.origin` / submodule 路径 + 是否在 workspace 内**（或等价），替代单条泛化 ERROR；文档 **OPERATIONS/README** 对「勿混装克隆、须跑工作区四轮 + 收尾 pin」更可扫一眼。
  - **可选：** pip **`--no-deps`** 等与 **BUG-007** 兼容的进一步强化（低频）。
- 预期收益：
  - 依规安装时 **`doctor` 一次过**；异常时 **少猜**是哪一只包跑偏。
- 影响范围：
  - **`bootstrap/src/bootstrap/doctor.py`**（诊断输出）；**`bootstrap/README.md` / `bootstrap/OPERATIONS.md`**
- spec 索引：
  - `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`（§4.1 四处 `pip install -e`、§6 `doctor`）
- plan 索引：`-`
- 备注：
  - **已实现（代码核对 2026-04-30）：** **`bootstrap/install_workspace_editables.py`**：`cwd` 严格顺序 **`vla_env_contract` → `runtime/webhook` → `tools/dify_upload` → `tools/feishu_fetch`**；循环后 **再在 `vla_env_contract` 执行一次** **`pip install -e .`**，注释写明：**对抗** webhook 装依赖留下的 **wheel / site-packages** 解析，对齐 plan A.3、`doctor` 预期。
  - **仍未做：** **`doctor`** 在 **`_workspace_import_paths_ok`** 失败分支 **不**逐包列出解析路径。
  - 与 **NTH-008** 相邻：**`doctor`/内嵌布局**已落地；本条是 **同上检查之上的排障体验**。
  - **场景 A / 跳过 `install-workspace-editables`：** ERROR **仍可出现**，不属于「模块 bug」，属环境与流程。

### 方案草案

- **`doctor` 失败时**（仍 **待评估 / 可选实现）：** 对四个包各打 **`find_spec`** 的实际路径一行 + **`_path_is_under_workspace`** 布尔，再 exit 1。
- **`install-workspace-editables` 收尾再 `-e` `vla_env_contract`：** **（已在 `install_workspace_editables.py` 落地）**
- 文档：**手册**继续强调 **`bootstrap install-workspace-editables`**；若仍报错，先看 **是否在克隆根重复 `-e`** 或 **改用干净解释器**/清 user site。

### 验收标准

- **依规路径：** 物化后只按文档执行 **`install-workspace-editables`**，`doctor` 在 **常见问题 B** 上 **不因缺「手工第二遍 pin」反复失败**。**（主力已由代码满足；脏环境除外。）**
- **`doctor`：** 若在 **仍为待实现** 的增强落地，则 FAIL 时 **可直接读出**是哪一包的解析偏离工作区。
- 与 **BUG-007** **无矛盾**表述（工作区四轮 **`cwd`** 仍为硬要求）。
