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
| NTH-002 | webhook 补齐 Dify 目标配置合同 | P1 | 已出 spec | 2026-04-26 | `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` | - | 当前 webhook 设计仅稳定覆盖 `dataset_id`，现已明确 `api_base`、`api_key` 走模块根 `.env`，`dataset_id` 必须运行时显式传入 |
| NTH-003 | RQ 并发多个 Cursor CLI 的设计与实现优化 | P1 | 待评估 | 2026-04-26 | `docs/superpowers/specs/2026-04-26-webhook-cursor-executor-design.md` | - | 当前 spec 已覆盖基础并发语义，后续需单独优化稳定性与实现细节 |
| NTH-004 | 根目录 .env 与各模块配置消费合同收口 | P1 | 已出 spec | 2026-04-26 | `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` | - | 已明确各模块直接消费根 `.env` 各自分组，LLM 不注入基础设施配置，legacy Feishu 维持兼容保留 |
| NTH-005 | 飞书文件夹-Dify 知识库-QA 合同一对一映射收口 | P1 | 已出 spec | 2026-04-26 | `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` | - | 已明确 `folder_token` 必须一对一命中 `dify_target_key`、`dataset_id` 与 `qa_rule_file`，Agent 不负责推断 |
| NTH-006 | 飞书 App 文件夹创建与权限初始化工具 | P1 | 已实现 | 2026-04-26 | `docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md` | `docs/superpowers/plans/2026-04-27-feishu-app-folder-onboard-implementation-plan.md` | 根目录 `onboard/` 已提供 `feishu-onboard` 包与单测、README，按 spec/plan 两阶段写根 `.env` 与 lark 初始化，详见正文 |
| NTH-007 | 管线执行工作区物理目录初始化（与入轨解耦） | P2 | 待评估 | 2026-04-27 | - | - | **生产不在维护仓目录跑任务**，而在**专门初始化的执行工作区**；`feishu_fetch`/手册「项目根」易与维护仓 clone 重合，须与 RQ 真实 cwd 区分并桥接（见正文） |
| NTH-008 | bootstrap 收尾：内嵌 runtime、废 junction、`doctor` 后探活与可选服务脚本 | P1 | 已实现 | 2026-04-28 | `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`（主）；`docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md`（**§3.4** 待 **Task 10** 对齐） | `docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md`（主）；`docs/superpowers/plans/2026-04-28-production-bootstrap-deployment-implementation-plan.md`（旧版 junction §，**Task 10** 废止） | 内嵌 runtime / **`bootstrap probe`** 定型：**`doctor`** → **`probe --no-http`**；服务起后全量 **`probe`**（**`WEBHOOK_PROBE_BASE` + `/health`**）；**§10 / production-bootstrap §3.4** **未**并入本条目 closure；增量 **NTH-009** |
| NTH-009 | 工作区 runtime / prompts 增量同步（免每次全量 bootstrap） | P3 | 待评估 | 2026-04-28 | - | - | 需求登记自 **`workspace-embedded-runtime-design.md` §5**；**无** spec/plan 前 **不**做 |
| NTH-010 | `bootstrap interactive-setup` 人机链串联（编排后续可复用 CLI） | P3 | 待评估 | 2026-04-28 | - | - | 接受工具分段复用；缺**同一交互流内**顺序编排，与 **NTH-006**/**NTH-008** 相邻 |
| NTH-011 | 工作区 `doctor`：pipeline 包须落工作区 — 与「同解释器混装克隆工作区 / `vla_env_contract` 被 wheel 顶掉 editable」 | P2 | 待评估 | 2026-04-28 | `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`（§4.1、§6、`doctor` plan A.3） | - | 与 **BUG-007**（`cwd`+`file:` 锚点）不同根因；见正文 |
| NTH-012 | `materialize-workspace` 只物化运行必要树（排除测试目录、排障/一次性脚本等） | P2 | 待评估 | 2026-04-29 | - | - | 减少执行工作区体积与误触非生产文件；实现须与 `doctor`/editable 路径一致，见正文 |

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
- 当前状态：已出 spec
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
  - -
- 备注：
  - 已与 `NTH-004` 合并收口。
  - 已确定 `dataset_id` 必须运行时显式传入，根 `.env` 不允许提供默认值。

### 方案结论

- `dataset_id` 必须由运行时显式传入。
- `api_base`、`api_key` 由 `dify_upload` 自己从根 `.env` 读取。
- LLM / `task_context.json` 不注入 Dify 静态连接配置。

### 验收标准

- webhook 侧明确 `api_base`、`api_key` 不进入运行时合同。
- `dify_upload` 的输入合同与 `dataset_id` 显式传入口径闭环。
- 根 `.env` 不再承担默认 `dataset_id` 注入职责。

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
- 当前状态：待评估
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
  - -
- 备注：
  - 已与 `NTH-002`、`NTH-004` 一并收口。
  - 核心约束是一对一绑定和显式注入，不接受运行时猜测。

### 方案结论

- 由 `webhook` 路由配置维护一对一映射，命中后显式注入 `folder_token`、`dify_target_key`、`dataset_id`、`qa_rule_file`。
- Agent 不负责推断 Dify 实例、目标知识库或 QA 合同。
- 根 `.env` 只负责 `dify_target_key -> Dify 静态实例配置`，不承担业务映射。

### 验收标准

- 能明确说清每个飞书文件夹对应哪一套 Dify 实例、哪一个知识库和哪一份 QA 合同。
- 不同飞书文件夹触发的业务合同不再依赖 Agent 推断。
- 新增或调整映射时，只需要改一处主配置，不会出现多处定义互相打架。

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
  - 该工具能自动创建对应的 App 文件夹，并把文件夹设置成企业内部可见。
  - 创建成功后，能拿到目标 `folder_token` 并回写到根 `.env`，供后续映射配置继续使用。
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
  - 重点是把“App 文件夹约束”和“token 回写配置”收口成可执行工具，而不是靠人工步骤维持。
  - 2026-04-27：已按 plan 在仓库根 `onboard/` 落地可编辑安装的 Python 包 `feishu-onboard`（入口 `feishu-onboard`），含校验、两阶段根 `.env` 原子写、飞书 token/建夹/公开权限、`lark-cli config init` 与 `show` 校验、编排与交互 CLI；`pytest` 覆盖核心路径；操作说明见 `onboard/README.md`；与 webhook 接根 `.env` 路由属并行后续工作，不在 NTH-006 本条目范围内。

### 方案草案

- 已采纳 plan：独立子包于 `onboard/`，不并入 webhook 运行时；按 spec 两阶段写（阶段 A 业务分组、阶段 B `FEISHU_FOLDER_ROUTE_KEYS` 门禁于 public + lark 均成功之后）。
- 原方案一/二/三中的方向已收敛为当前包形态；批量初始化、自 `webhook` 派生 `folder_routes.example.json` 等仍为 plan 声明的非本条目必达项。

### 验收标准

- 能通过飞书 OpenAPI 基于 App 身份创建出可用于本仓库的 App 文件夹。
- 创建后能自动把文件夹设置为企业内部可见，避免继续依赖人工补权限（失败时按 spec 进入部分完成态，不写索引）。
- 工具能拿到正确的 `folder_token` 并稳定回写到根 `.env` 指定配置项（与 spec §5 键名一致，含两阶段与续跑/冲突语义，以实现与 `onboard` 内单测为准）。

## NTH-007 管线执行工作区物理目录初始化（与入轨解耦）

- 提出时间：2026-04-27
- 当前状态：待评估
- 优先级：P2
- 背景/问题：
  - **生产现实（须默认成立）：** 实际跑 webhook/RQ/Cursor 管线任务时，**不可能**在「本维护仓 Git 工作副本」目录下执行；任务 cwd 是**单独搭好的执行工作区**（另一物理路径）。维护仓只负责源码与模板；文档、验收手册若以维护仓为「项目根」示例，仅方便本地开发，**不表示生产同路径**。
  - `feishu-onboard`（NTH-006）成功路径为：飞书 App 夹、两阶段写**其认定的仓根** `.env`、在**同一目录**执行 `lark-cli config init`。
  - 它不生成「单独一套用于 RQ / webhook 触发生产任务的 Cursor 工作区」目录树；根 `AGENTS.md` 亦写明本仓库 ≠ 单次任务的运行时工作区。
  - **断链（与文档/示例默认假设不一致）：** `feishu_fetch` 及若干操作说明依赖「单一 workspace 根」（根 `.env` 父目录 + `lark-cli` 子进程 `cwd`）。示例与人工验收常默认该根 = **本维护仓 Git clone 顶层**，但**正式生产**里任务往往在**另一物理目录**（单独初始化的执行工作区、镜像内路径、RQ worker 工作目录等）启动；若不在该执行根重复同源 `.env` / lark 初始化，或不用 `FEISHU_FETCH_ENV_FILE` 等显式指回真源，则「入轨已完成」与「抓取可跑」在路径上**不接续**。当前缺口无独立 spec/plan，易让人以为「当前目录」永远是维护仓。
  - 若运维期望「入轨=顺带落一个物理生产工作区（拷 `prompts`→`AGENTS`、物化 `rules` 等）」，当前工具不包含该步，易与职责边界产生误解。
- 目标：
  - 明确入轨与「执行工作区」初始化是否拆分；若需要，用独立 spec/plan 定义目录结构、与根 `.env` 的关系、谁负责拷贝/物化模板、**维护仓根与执行区根如何对齐**（复制、挂载、环境变量、禁止混用等）。
  - 文档层：凡描述「项目根 / 仓库根 / cwd」须能映射到**维护仓**或**执行工作区**其一，避免默认二者同一路径。
  - 可选：CLI 子命令、安装脚本或部署流水线节点，在指定路径搭好执行区但不重复 NTH-006 已有能力。
- 预期收益：
  - 减少「以为 onboard 会建工作区」的配置事故。
  - 需要物理隔离时有一致、可复现的搭盘方式。
- 影响范围：
  - 与 `onboard/`、工作区模板 `prompts/**`、未来执行器/部署文档的边界说明
- spec 索引：-
- plan 索引：-
- 备注：
  - 不反向要求改动已落地的 NTH-006 行为，除非经评审后合并需求。
  - 易与「维护仓 = 执行根」混读的文档包括但不限于：`feishu_fetch/人工验收操作手册.md`、`onboard/操作手册.md`；落地本条目时应统一用语或加边界说明。
  - 2026-04-27：用户补充登记——**生产侧任务目录 = 专用执行工作区，非本仓库 clone 根**；与上条「断链」同一问题，归入 NTH-007，不单开 ID。

### 方案草案

- 方案一：仅文档在 README / 操作手册中强化「维护仓根 ≠ 正式执行工作区根」及桥接方式（`FEISHU_FETCH_ENV_FILE`、执行根 `.env`、lark `cwd`），不新增实现。
- 方案二：独立小工具或 `feishu-onboard workspace init <path>`，从模板生成目录并提示与根 `.env` 同机/同盘约束。
- 方案三：生产工作区全由现有外部编排（镜像、CI、RQ 机）完成，本仓只维护模板资产。

### 验收标准

- 能向操作者说清：入轨成功 ≠ 已创建独立生产工作区目录；若需要后者，有明确入口或文档步骤。
- 能向操作者说清：**正式跑抓取时的 workspace 根** 可以与 **跑 `feishu-onboard` 写 `.env` 的目录** 不同，但必须用约定方式对齐（同源配置或显式 `FEISHU_FETCH_ENV_FILE` 等），否则属于部署/初始化断链而非模块 bug。
- 若实现方案二，有最小验收（目录结构、`AGENTS`/`rules` 来源、不泄露密钥）。

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
  - **版本迭代：** 与 **`workspace-embedded-runtime-design.md` §5** 一致——**每次**新版本 **完整重新 bootstrap**；**不**在本条 plan 做「增量同步 runtime」。远期需求见 **NTH-009**。

### 方案草案

- 探活：候选矩阵 `REDIS_URL`、`FOLDER_ROUTES_FILE` 可读性、`DIFY_TARGET_*` 组完整性、`WEBHOOK_PROBE_BASE` + **`GET /health`**（全量）；`interactive-setup` 末尾：**`doctor`** → **`bootstrap probe --no-http`**；生产起服务后再 **`bootstrap probe`**（无 **`--no-http`**）；CI/Merge：`SkipProbe` / `-SkipProbeHttp` 见 **`2026-04-28-workspace-embedded-runtime-implementation-plan.md`**。
- 内嵌 runtime：以 **`workspace-embedded-runtime-design.md`** §3 + §10 为 PR 清单；`doctor` 增加实目录/禁联接克隆校验（§6）。
- CI：外联探针默认跳过或 `SkipProbe` 同级开关。

### 验收标准

- **代码：** **`tools/*`** 路径 **无** `ensure_junction`；单测覆盖拷贝物化；**§8** 整机与文档一致。
- **探活：** 文档写明与人机签字关系；无密钥不强行打生产 API。
- 与现有 Task 14 闸门脚本兼容或可追加可选一步。

## NTH-009 工作区 runtime / prompts 增量同步（免每次全量 bootstrap）

- 提出时间：2026-04-28
- 当前状态：待评估
- 优先级：P3
- 背景/问题：
  - **`2026-04-28-workspace-embedded-runtime-design.md` §5** 明确 **本轮** **不**做在线/增量升级：发版依赖 **全量重新 bootstrap**。
  - **远期** 可能希望：在 **`{WORKSPACE_ROOT}`** 已存在时，仅用 **覆盖拷贝 `runtime/webhook`、`tools/*`** + **`pip install -e .`** + **重启服务**（及/或与 **`prompts` → `AGENTS.md`/`rules/`** 编排成 **单一子命令**），减少重复全量步骤与停机窗口。
- 目标：
  - **待** 有独立 **design spec + implementation plan** 后再定：同步粒度（全量覆盖 vs diff）、与 **工作区 `.env`** / **任务目录** 的兼容、回滚与验收。
- 预期收益：
  - 大版本迭代外，小版本或热修时缩短运维路径（若安全可证）。
- 影响范围：
  - **`bootstrap/`**（潜在新子命令或 `materialize-workspace` 模式）、**`bootstrap/README.md`**、**`workspace-embedded-runtime-design.md`** 将来修订 **§5**
- spec 索引：`-`（出稿后替换）
- plan 索引：`-`
- 备注：
  - **不**阻塞 **NTH-008**；**无** spec 前 **禁止**当合同实现增量同步。

### 方案草案

- （空）

### 验收标准

- （空）

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

## NTH-011 工作区 `doctor`：pipeline 包须落工作区 — 与「同解释器混装克隆工作区 / `vla_env_contract` 被 wheel 顶掉 editable」

- 提出时间：2026-04-28
- 当前状态：待评估
- 优先级：P2
- 背景/问题：
  - **`bootstrap doctor --workspace <WS>`** 要求 `feishu_fetch`、`dify_upload`、`webhook_cursor_executor`、`vla_env_contract` 的 **`importlib.util.find_spec` 解析路径**均落在 **`{WORKSPACE_ROOT}`** 下（plan A.3 / `doctor.py` `_workspace_import_paths_ok`）。
  - **现象 A：** 同一 **`py -3.12`** 曾在**维护仓克隆根**对 pipeline 包做过 **`pip install -e`**，运行 `doctor` 时仍解析到 **克隆路径**，报错 **`pipeline packages must resolve under workspace root`**。
  - **现象 B：** 在 **`{WS}/runtime/webhook`** 执行 **`pip install -e .`** 时，pip 对依赖 **`vla-env-contract @ file:../../vla_env_contract`** 可能 **再装一份 wheel 到 user `site-packages`**，使 **`vla_env_contract`** 的 **`find_spec`** 指向 **`site-packages`** 而非 **`{WS}/vla_env_contract/src/...`**，同样触发上述 ERROR；**补打** **`pip install -e {WS}/vla_env_contract`**（且宜在 webhook 装完后**最后**执行）可恢复。
  - 与 **BUG-007**（错误 **`cwd`** 下 `file:` 路径断裂、errno 2）**不同**：本条是 **「已能装上，但解释器优先解析到仓外 / 非 editable 副本」** 的运维体验与易错点。
- 目标：
  - 减少 **无意混装** 与 **wheel 覆盖 editable** 的发生，或 **失败时指明**哪一个包解析到了哪条路径（便于一次看懂）。
  - 候选方向（互斥或组合）：**`install-workspace-editables`** 固定顺序且 **装完 webhook 后强制再 `-e` 工作区 `vla_env_contract`**；**`doctor` stderr** 打印各包 `spec.origin` / 首条 `submodule_search_locations`；文档 **OPERATIONS / README** 单列「最后补 `vla_env_contract`」；pip 侧 **`--no-deps`** 或依赖元数据调整（需评估与 **BUG-007** 兼容）。
- 预期收益：
  - 首次物化后 **`doctor` 一次过**比例提高；排障不靠口头经验。
- 影响范围：
  - **`bootstrap/src/bootstrap/doctor.py`**、**`install_workspace_editables`（若有）**、**`bootstrap/README.md` / `bootstrap/OPERATIONS.md`**
- spec 索引：
  - `docs/superpowers/specs/2026-04-28-workspace-embedded-runtime-design.md`（§4.1 四处 `pip install -e`、§6 `doctor`）
- plan 索引：`-`
- 备注：
  - 与 **NTH-008**（内嵌 runtime / `doctor` 已落地）相邻：属 **已落地能力上的易用性/鲁棒性** 缺口，**不**重复登记「内嵌树」本身。

### 方案草案

- **`doctor` 失败时**：对四个包各打一行 **实际解析路径** + 是否 **`_path_is_under_workspace`**，避免只给泛化 ERROR。
- **`install-workspace-editables` 收尾**：在 **`runtime/webhook`** 之后 **无条件再执行** **`pip install -e {workspace}/vla_env_contract`**（或与 pip 行为对齐的等价物）。
- 文档：**手册「四处安装」后加粗一句** — 若装过 webhook 仍报 `vla_env_contract` 不在工作区，**再对工作区根 `vla_env_contract` 执行一次 `-e`**。

### 验收标准

- 在「干净 user site-packages + 仅按文档工作区四处安装」路径下，**不**需人工发现「最后补 `vla_env_contract`」即可通过 `doctor`；**或** 文档与 CLI 输出使该步骤 **显式、不可漏**。
- 与 **BUG-007** 已修复路径 **无**冲突表述（`cwd` 锚点仍须正确）。

## NTH-012 `materialize-workspace` 只物化运行必要树（排除测试目录、排障/一次性脚本等）

- 提出时间：2026-04-29
- 当前状态：待评估
- 优先级：P2
- 背景/问题：
  - 现 **`copy_materialize_subtree` / `materialize-workspace`** 从克隆整树拷入执行工作区，**`tests/`**、**`__pycache__`**、维护侧 **一次性排障/验证脚本** 等一并过去，执行区臃肿且易误导（非生产入口）。
- 目标：
  - 物化白名单或忽略规则：**仅**运行与 `install-workspace-editables` / **`doctor`** 所需源码与元数据（**`pyproject.toml`、`src/`、包内非测资源**等）；**默认不拷** **`tests/`**、**`.pytest_cache`**、明显 **dev-only** 脚本（具体名单落地时与克隆树对照校准）。
- 预期收益：
  - 工作区更小、更清晰；降低误运行维护仓测试树的风险。
- 影响范围：
  - **`bootstrap/src/bootstrap/copy_trees.py`**（或 **`materialize.py`**）、**`bootstrap/tests/test_materialize.py`**、必要时 **production-bootstrap** 文档中「物化产物」描述。
- spec 索引：`-`
- plan 索引：`-`
- 备注：
  - 须与 **NTH-008 / workspace-embedded-runtime**：工作区内 **仍**能 **`pip install -e`** 与 import；若某包测试目录被 tooling 误依赖需单列例外。

### 方案草案

- 扩展 **`materialize_copy_ignore`**（或等价）：`tests`、`__pycache__`、`.pytest_cache`、按需 `scripts/` 子集。
- **CI/验收**：`test_materialize` 断言 **目标树无** `tests/` 或抽样 `webhook` **无** `tests/`。

### 验收标准

- 干净物化后执行区 **无**（或文档声明的极少数例外下 **无**）克隆侧 **`tests/`** 目录；**`doctor` + 生产起服务路径** 不受影响。
