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
- 当前状态：待评估
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
