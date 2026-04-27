# Webhook Cursor Executor Design

## 修订说明（2026-04-27 Cursor CLI 可执行：仅 PATH、废弃 `CURSOR_CLI_COMMAND`）

本文件以下正文保留原文，不直接改写原设计内容。若与正文 §13.1「建议新增配置项」等旧表述冲突，以本修订说明为准：

- **可执行文件**：`webhook` 启动 Cursor 子进程时**固定**命令名 `cursor`，在运行时用 `shutil.which` 从 **PATH** 解析**绝对路径**后再 `subprocess.run`；**禁止**在根 `.env` 或**部署环境变量**中配置可执行文件路径/别名（已废弃的 `CURSOR_CLI_COMMAND` 若仍存在，**拉取 `ExecutorSettings` 即 `ValueError`，HTTP/RQ 进程无法启动**）。
- **根 `.env` 中仍与 Cursor 相关的合法键**（以 `webhook/src/webhook_cursor_executor/settings.py` 为准）：`CURSOR_CLI_MODEL`、`CURSOR_CLI_CONFIG_PATH`（及各类 TTL、Redis、路由文件路径等）。**勿**与正文里「`cursor_cli_*=…` 连等号」的示意混为一谈；环境变量名以 `settings` 的 `Field(alias=...)` 为准。
- **运行时失败语义**：若 PATH 上找不到 `cursor`，`launch` 会结束本次 run，summary 含 `cursor_not_in_path:` 前缀，退出码 127 一类（以实现对齐为准）。
- **升级自旧版**：根 `.env`、K8s/系统环境变量、CI secret 中若仍设置 `CURSOR_CLI_COMMAND`，**必须整行/整键删除**，并保证运行 `webhook`/`rq worker` 的账户 **PATH 能解析到 `cursor`**。详见 `webhook/操作手册.md` 升级小节。

## 修订说明（2026-04-27 onboard 初始化前置条件补充）

本文件以下正文保留原文，不直接改写原设计内容。

针对 `onboard` 当前正文与 `lark-cli` 初始化 owner 已确认收口到 `onboard` 的新口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- 第一版中，目标工作区的 `lark-cli` 首次初始化由 `onboard` 负责；`webhook` 只假设目标工作区已经完成该前置初始化
- `webhook` 不负责在每次任务启动前重新执行 `lark-cli config init`
- `webhook` 不负责给 `feishu_fetch` 注入 `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 或其他飞书凭证来替代工作区初始化
- 若正文中仍出现“onboarding 只负责产出 JSON 路由配置”一类旧表述，应按当前口径理解为：`onboard` 负责创建飞书 App 文件夹、回写根 `.env` 真源，并在当前工作区完成一次 `lark-cli` 初始化
- `launch_cursor_run_job` 的环境前置条件应补充理解为：目标工作区已由 `onboard` 完成必要初始化，至少包括当前工作区 `lark-cli` 可执行且已完成配置
- 若目标工作区未完成 `onboard`，或当前工作区的 `lark-cli` 尚未初始化，则该次运行应按“环境前置条件未满足”失败，而不是由 `webhook` 运行时自动修复
- 这种失败场景下，`webhook` 负责记录清晰错误原因并结束本次 run；不自动补做 `config init`，不临时切换飞书应用身份
- 后续实现与测试应新增一条明确口径：当工作区未初始化或 `lark-cli` 未完成配置时，任务失败原因必须可区分为环境前置条件问题，而不是混淆为业务路由或正文抓取逻辑错误
- 相关联动口径以 [2026-04-26-feishu-app-folder-onboard-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md) 与 [2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 的当前正文为准

## 修订说明（2026-04-27 评审收口）

本文件以下正文保留原文，不直接改写原设计内容。

针对本轮评审与 `onboard` 当前正文口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- `folder_token -> dify_target_key + dataset_id + qa_rule_file` 的业务映射真源来自仓库根 `.env`
- `webhook` 后续对 route 的解析输入，必须直接来自根 `.env` 中的显式 route 索引和 route 分组
- `webhook/config/folder_routes.example.json` 不再作为运行时真源，只能作为示例文件或由根 `.env` 导出的派生产物
- `webhook` 路由结果、文档快照与 `task_context.json`，都必须显式包含 `dify_target_key`、`dataset_id`、`qa_rule_file`
- 旧正文中的快照示例若缺少 `dify_target_key`，应按合同缺失理解，而不是视为可省略字段
- 根 `.env` 中的 `FEISHU_FOLDER_<KEY>_QA_RULE_FILE` 必须保存运行时工作区 `rules/` 目录下的相对路径，例如 `rules/qa/folders/team_a.mdc`
- 当前单工作区抓取链路默认只服务于根 `.env` 中这一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 对应的同一飞书应用 bot 身份
- `folder_token` 只承担业务分流职责，不承担在运行时切换飞书应用身份职责；若目标文档对该同一应用不可访问，应按权限问题失败
- 若正文中仍出现“onboarding 只负责产出 JSON 路由配置”“运行时只需要 `dataset_id`”或“`folder_token` 只映射到 `qa_rule_file + dataset_id`”一类旧表述，均按本修订说明覆盖理解

## 修订说明（2026-04-26 NTH-006 联动补充）

本文件以下正文保留原文，不直接改写原设计内容。

针对 `NTH-006 飞书 App 文件夹创建与权限初始化工具` 与新的“.env 唯一真源”口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- `folder_token -> dify_target_key + dataset_id + qa_rule_file` 的业务映射真源来自仓库根 `.env`
- `webhook/config/folder_routes.example.json` 不再作为运行时真源，只能作为示例文件或由根 `.env` 派生出的产物
- `onboard` 负责创建飞书 App 文件夹并把 route 真源写回根 `.env`
- `webhook` 后续应以根 `.env` 中的显式 route 索引和 route 分组作为解析输入
- 当前单工作区抓取链路默认只服务于根 `.env` 中这一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 对应的同一飞书应用 bot 身份
- `folder_token` 只承担业务分流职责，不承担在运行时切换飞书应用身份职责；若目标文档对该同一应用不可访问，应按权限问题失败
- 若正文中仍出现“onboarding 只负责产出 JSON 路由配置”一类旧表述，均按本修订说明覆盖理解

## 修订说明

本文件以下正文保留原文，不直接改写原设计内容。

针对后续已确认的 `NTH-002`、`NTH-004`、`NTH-005`，现补充以下修订口径；若与正文旧表述冲突，以本修订说明为准：

- `folder_token` 的业务映射已收口为：
  - `folder_token -> dify_target_key + dataset_id + qa_rule_file`
- `task_context.json` 的运行时显式注入字段，至少应包含：
  - `dify_target_key`
  - `dataset_id`
  - `qa_rule_file`
- Agent 不负责推断 Dify 目标：
  - 调用上传工具时，必须显式传入 `dify_target_key` 与 `dataset_id`
- 根 `.env` 不再承担默认业务目标注入职责：
  - 不允许依赖默认 `DIFY_DATASET_ID`
  - Dify 实例静态配置由 `dify_target_key` 命中
- Dify 静态配置解析口径以 [2026-04-26-root-env-and-dify-target-contract-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md) 为准
- 若正文中仍出现“只注入 `dataset_id` 即可”或“`folder_token` 只映射到 `qa_rule_file` 与 `dataset_id`”等旧表述，均按本修订说明覆盖理解

## 1. 背景与目标

本设计用于重构旧的 `feishu_webhook` 参考实现，在 `c:\WorkPlace\NewVLA\webhook` 下建设一套新的 webhook 调度模块。

旧代码只作参考，不延续其“RQ worker 调 Python handler”的业务模型。新设计保留队列层与后台执行器，但将执行目标改为：

- 接收飞书 webhook 事件
- 做协议层幂等
- 按 `document_id` 合并任务并控制同文档互斥
- 按 `folder_token` 命中对应的业务分流配置
- 在目标目录启动 Cursor CLI
- 通过 LLM 友好的任务单把上下文交给 workspace 内 Agent 执行

本模块只负责“触发、调度、启动”。
本模块不负责：

- 飞书正文拉取
- Dify 上传
- 任务内业务编排
- workspace 内规则内容本身

## 2. 设计原则

- 机器可控：调度逻辑不依赖 LLM 理解是否准确
- LLM 友好：任务说明先讲目标，再给附件
- 目录稳定：每次运行按 `run_id` 创建独立目录，任务注入与产出均放在该目录内，避免互相覆盖
- 边界清晰：webhook 只负责触发和调度；workspace 内 Agent 负责业务执行
- 不再使用“大量 env / 生硬 JSON 拼 prompt”作为主要注入方式

## 3. 非目标

- 不在第一版实现复杂优先级调度
- 不在第一版实现按目录限流
- 不在第一版实现任务取消或强杀 Cursor CLI
- 不在第一版实现复杂表达式路由
- 不在第一版实现长期审计数据库
- 不在第一版实现巡检型恢复任务

## 4. 总体架构

```text
Feishu Webhook
    |
    v
[Webhook HTTP App]
- 验签 / 解密
- 解析事件
- 提取 document_id
- event_id 幂等
- 更新 document snapshot
- 投递 schedule 任务
    |
    v
[RQ Queue]
    |
    v
[Background Executor]
- schedule_document_job
- launch_cursor_run_job
- finalize_document_run_job
    |
    v
[Target Workspace]
- AGENTS.md
- rules/
- .cursor_task/{run_id}/
  - task_prompt.md
  - task_context.json
  - outputs/
```

## 5. 核心语义

### 5.1 事件层

- `event_id` 只承担飞书协议层幂等
- 目的：防失败重推、至少一次投递造成的重复消费

### 5.2 文档层

- `document_id` 是新系统调度主键
- 不同 `document_id` 可并发
- 相同 `document_id` 尽量保证不并发
- 同一文档短时间多次变更，采用“最后一次生效”语义

### 5.3 执行层

- 后台执行器不直接执行业务代码
- 后台执行器只负责：
  - 查最新快照
  - 控制互斥
  - 解析目标 workspace
  - 生成任务单
  - 启动 Cursor CLI
  - 回写运行状态

## 6. 任务生命周期

```text
1. webhook 收到飞书事件
2. event_id 幂等成功
3. 更新 snapshot + version
4. enqueue schedule_document_job(document_id, version)

5. schedule_document_job
6. 若 version 已旧 -> 跳过
7. 若抢到 runlock -> enqueue launch_cursor_run_job
8. 若没抢到 -> 写 rerun 标记并结束

9. launch_cursor_run_job
10. 解析 workspace
11. 创建 `run_id` 独立目录并写入任务注入文件
12. 启动 Cursor CLI
13. enqueue finalize_document_run_job

14. finalize_document_run_job
15. 释放 runlock
16. 若 rerun 存在且版本更新 -> 重新 enqueue schedule_document_job
17. 否则结束
```

## 7. Redis 键设计

### 7.1 `webhook:event_seen:{event_id}`

- 类型：`string`
- 值：`1`
- TTL：`24h`
- 用途：飞书事件协议层幂等
- 写入方式：`SET key 1 NX EX 86400`
- 语义：
  - 成功：继续处理
  - 失败：说明重复事件，直接返回成功响应

### 7.2 `webhook:doc:snapshot:{document_id}`

- 类型：`string(json)`
- TTL：`24h`
- 用途：保存该文档最后一次有效事件的完整调度快照

示例：

```json
{
  "event_id": "evt_xxx",
  "document_id": "doc_xxx",
  "folder_token": "fld_xxx",
  "event_type": "drive.file.updated_v1",
  "qa_rule_file": "rules/fld_xxx_qa.md",
  "dataset_id": "dataset_xxx",
  "workspace_path": "C:\\workspaces\\pipeline",
  "received_at": 1777139000,
  "version": 12
}
```

### 7.3 `webhook:doc:version:{document_id}`

- 类型：`string(integer)`
- TTL：`24h`
- 用途：文档版本号，自增用于淘汰旧调度任务
- 写入方式：每次快照更新时 `INCR`

### 7.4 `webhook:doc:runlock:{document_id}`

- 类型：`string`
- 值：当前 `run_id`
- TTL：配置化，默认 `3h`
- 用途：同文档互斥执行的第一层保护
- 写入方式：`SET key run_id NX EX ttl`

第一版约束：

- 采用 TTL 锁，不引入续租、心跳或额外守护线程
- 目标是“尽量保证同文档不并发”，而不是为了极端场景引入重型机制
- `DOC_RUNLOCK_TTL_SECONDS` 应大于等于 `CURSOR_RUN_TIMEOUT_SECONDS`，并留出缓冲时间
- 若异常退出导致锁残留，依赖 TTL 自动释放，并由后续 webhook 事件重新驱动调度

### 7.5 `webhook:doc:rerun:{document_id}`

- 类型：`string(json)`
- TTL：`24h`
- 用途：标记“当前任务结束后，需按最新版本补跑一次”

示例：

```json
{
  "required": true,
  "target_version": 13,
  "updated_at": 1777139000
}
```

### 7.6 `webhook:run:context:{run_id}`

- 类型：`string(json)`
- TTL：`1d ~ 3d`
- 用途：保存一次运行的临时上下文，方便排障与结果关联

示例：

```json
{
  "run_id": "run_xxx",
  "document_id": "doc_xxx",
  "version": 12,
  "event_id": "evt_xxx",
  "workspace_path": "C:\\workspaces\\kb_default",
  "status": "running"
}
```

## 8. TTL 策略

TTL 不是主逻辑，而是异常场景的兜底清理机制。

- `event_seen` 需要 TTL：防重复投递记录无限增长
- `runlock` 必须 TTL：防执行器异常退出后文档永久锁死
- `snapshot` 与 `rerun` 需要 TTL：防临时调度状态长期残留
- 任务正常结束后应主动清理；TTL 负责处理异常退出

推荐默认值：

- `EVENT_SEEN_TTL_SECONDS=86400`
- `DOC_SNAPSHOT_TTL_SECONDS=86400`
- `DOC_RUNLOCK_TTL_SECONDS=10800`
- `DOC_RERUN_TTL_SECONDS=86400`
- `CURSOR_RUN_TIMEOUT_SECONDS=7200`

## 9. RQ 任务类型

### 9.1 `schedule_document_job`

职责：

- 读取文档最新快照
- 判断当前任务版本是否已过时
- 尝试获取同文档运行锁
- 决定是直接发起启动，还是只写补跑标记

输入：

```json
{
  "document_id": "doc_xxx",
  "version": 12
}
```

处理规则：

- 若 `snapshot.version != version`，直接跳过
- 若成功获取 `runlock`，enqueue `launch_cursor_run_job`
- 若获取失败，更新 `rerun.target_version` 为当前最新版本

### 9.2 `launch_cursor_run_job`

职责：

- 验证当前运行锁仍归本次 `run_id`
- 解析目标 workspace
- 生成任务单与上下文文件
- 启动 Cursor CLI
- 记录运行状态并投递 finalize

输入：

```json
{
  "document_id": "doc_xxx",
  "version": 12,
  "run_id": "run_xxx"
}
```

### 9.3 `finalize_document_run_job`

职责：

- 写入本次运行结果
- 清理运行上下文
- 释放文档运行锁
- 检查是否存在更新版本的补跑需求
- 如需要则重新 enqueue `schedule_document_job`

输入：

```json
{
  "run_id": "run_xxx",
  "document_id": "doc_xxx",
  "version": 12,
  "exit_code": 0,
  "status": "succeeded",
  "summary": "..."
}
```

## 10. Workspace 配置映射结构

系统只维护一个统一的管线工作区。
不再按飞书 `folder` 切分不同 `workspace`。
不同 `folder` 只承担业务分流职责。

因此，第一版不再使用“多 workspace 路由”模型，而是使用“单 workspace + folder 业务映射”模型。
后续 onboarding 只负责产出这份配置。

推荐结构：

```json
{
  "pipeline_workspace": {
    "path": "C:\\workspaces\\pipeline",
    "cursor_timeout_seconds": 7200
  },
  "folder_routes": [
    {
      "folder_token": "fld_team_a",
      "qa_rule_file": "rules/team_a_qa.md",
      "dataset_id": "dataset_team_a"
    }
  ]
}
```

解析规则：

- 所有任务都进入同一个 `pipeline_workspace.path`
- 根据 `folder_token` 命中 `folder_routes`
- 命中后得到：
  - `qa_rule_file`
  - `dataset_id`
- 未命中 `folder_token` 时，任务失败，不启动 Cursor CLI

第一版推荐仅支持以下匹配维度：

- `folder_token`

## 11. 机器合同

机器合同用于 Redis 状态机、RQ 入参、运行记录和排障，不直接作为 LLM 主输入。

字段：

- `schema_version`
- `run_id`
- `event_id`
- `document_id`
- `folder_token`
- `event_type`
- `snapshot_version`
- `qa_rule_file`
- `dataset_id`
- `workspace_path`
- `trigger_source`
- `received_at`
- `cursor_timeout_seconds`

示例：

```json
{
  "schema_version": "1",
  "run_id": "run_20260426_001",
  "event_id": "evt_xxx",
  "document_id": "doc_xxx",
  "folder_token": "fld_xxx",
  "event_type": "drive.file.updated_v1",
  "snapshot_version": 12,
  "qa_rule_file": "rules/fld_xxx_qa.md",
  "dataset_id": "dataset_xxx",
  "workspace_path": "C:\\workspaces\\pipeline",
  "trigger_source": "feishu_webhook",
  "received_at": "2026-04-26T10:00:00Z",
  "cursor_timeout_seconds": 7200
}
```

## 12. LLM 任务单合同

LLM 主输入应为自然语言任务单，不再以大量 env 或生硬 JSON 作为主要注入方式。
`task_context.json` 不是自动注入到模型上下文中的隐式信息，而是一个需要由 Agent 显式读取的补充文件。

任务单必须明确：

- 任务来源：飞书 webhook 自动触发
- 任务目标：按当前 workspace 的 `AGENTS.md` 与规则执行文档处理流程
- 处理对象：明确写出 `document_id`
- `AGENTS.md` 只承载统一主流程，不维护 `folder_token -> qa_rule_file` 的静态映射
- 必读材料：
  - `AGENTS.md`
  - `rules/`
  - `.cursor_task/{run_id}/task_context.json`
- 明确动作：
  - 先读取 `.cursor_task/{run_id}/task_context.json`
  - 再读取 `task_context.json` 中指定的 `qa_rule_file`
- 执行约束：
  - 不伪造工具结果
  - 若规则要求调用工具，按规则执行
  - 不假设用户会在运行中补充额外上下文
  - 不从仓库文档或静态规则中自行推断 Dify 目标
  - `dataset_id` 必须以 `task_context.json` 中的显式注入值为准

示例：

```md
你正在处理一次由飞书 webhook 自动触发的任务。

任务目标：
- 按当前工作区内的 `AGENTS.md` 与规则文件执行该文档的后续处理流程。
- 本次处理对象为：`document_id=doc_xxx`。
- 触发事件类型为：`drive.file.updated_v1`。

执行前必须先阅读：
- `AGENTS.md`
- `rules/` 目录
- `.cursor_task/run_20260426_001/task_context.json`

任务要求：
- 这是一次自动触发任务，不要假设用户会补充额外上下文。
- 你必须先读取 `.cursor_task/run_20260426_001/task_context.json`，再继续后续任务。
- 你必须再读取 `task_context.json` 中指定的 QA 规则文件。
- 如果规则要求调用工具，按规则执行。
- 不要伪造工具结果。
- 如果遇到阻塞信息缺失，应基于已有规则和上下文先完成可完成部分。
- 最终结果需要上传到 `task_context.json` 中指定的 Dify `dataset_id`。

补充说明：
- 本次任务来源：`feishu_webhook`
- 统一工作区：`pipeline_workspace`
- 运行实例：`run_20260426_001`
```

## 13. Launch 阶段文件产物

后台执行器在目标 workspace 中生成：

- `.cursor_task/{run_id}/task_prompt.md`
- `.cursor_task/{run_id}/task_context.json`
- `.cursor_task/{run_id}/outputs/`

说明：

- `.cursor_task/{run_id}/` 是一次运行的独立工作目录
- 所有任务注入文件与运行产物都放在该目录下
- `task_prompt.md` 是 LLM 主输入
- `task_context.json` 是机器合同的文件化副本，也是需要由 Agent 显式读取的补充上下文文件
- `outputs/` 用于存放本次运行产生的附加产物，例如结果摘要、运行日志、状态文件或后续需要回收的元数据
- 不应把这些临时任务文件放到 `rules/` 目录下
- 目录按 `run_id` 隔离，避免连续补跑覆盖前一次产物

### 13.0.1 任务目录原则

`.cursor_task/{run_id}/` 不是可选缓存目录，而是第一版实现必须遵守的任务工作目录约定。

硬性要求：

- 每次任务启动都必须创建独立的 `run_id` 目录
- 单次任务的所有注入物都必须放在该目录下
- 单次任务的所有运行产出也必须放在该目录下
- 不允许把任务级临时文件散落到 workspace 根目录
- 不允许把任务级临时文件写入 `rules/`、`AGENTS.md` 所在目录或其他长期配置目录

该原则的目的：

- 让一次任务的输入、输出、日志、状态天然聚合
- 避免多次任务互相覆盖
- 避免补跑任务污染上一轮产物
- 便于问题排查、失败回收和后续清理策略

第一版至少应保证以下内容统一落在 `.cursor_task/{run_id}/` 下：

- `task_prompt.md`
- `task_context.json`
- `outputs/`
- 可选的运行日志、结果摘要、状态标记文件

## 13.1 Cursor CLI 调用约定

第一版 `launch` 阶段采用默认 agent 模式启动 Cursor CLI，不显式传 `--mode ask` 或 `--plan`。
模型固定为 `composer-2-fast`。

原因：

- `ask` 模式偏只读问答，不适合作为真实 webhook 任务执行形态
- `plan` 模式同样不适合作为默认运行态
- 实测可行的最小链路是：读取 `task_prompt.md` 内容，并将其作为 Cursor CLI 的初始 prompt 传入
- `agent --print` 当前没有稳定的 `--max-mode` 顶层参数
- 交互式 CLI 中可通过 `/max-mode on` 切换 Max Mode，但这条路径不适用于无人值守自动化

约定：

- 使用默认 agent 模式
- 使用 `--model composer-2-fast`
- `task_prompt.md` 作为主提示词来源
- `task_context.json` 不假设为自动注入，而由 `task_prompt.md` 明确要求 Agent 先读取
- 后台执行器负责在调用前把 `task_prompt.md` 内容读出并作为初始 prompt 传给 Cursor CLI

### 13.1.1 无人值守 Max Mode

本设计中的 webhook -> RQ -> Cursor CLI 链路是无人值守自动化，不依赖交互式输入 `/max-mode on`。

因此，Max Mode 采用 **spawn 前同步 Cursor CLI 配置文件** 的方式开启，而不是依赖：

- 不存在或不稳定的 `--max-mode` 顶层参数
- 初始 prompt 中的 slash command

推荐做法：

- 在每次真正调用 `agent` 之前
- 读取 Cursor CLI 配置文件
- 将顶层 `maxMode` 写为 `true`
- 若存在对象 `model`，则将 `model.maxMode` 也写为 `true`
- 完成后再 spawn `agent`

推荐配置文件路径：

- 默认：`~/.cursor/cli-config.json`
- 允许通过配置覆盖为其他路径

示意：

```json
{
  "maxMode": true,
  "model": {
    "maxMode": true
  }
}
```

实现要求：

- 在 `launch_cursor_run_job` 真正拉起 Cursor CLI 前执行该同步
- `Max Mode` 是 v1 必须项，不能静默降级为 non-max
- 若配置文件不存在，第一版应创建最小配置文件后再继续 spawn
- 若写入失败，应将本次 launch 视为失败并记录原因，而不是继续以 non-max 模式运行
- 若 IDE 也会并发修改同一文件，应允许通过配置关闭该同步逻辑，避免竞态

第一版建议新增配置项：

- `cursor_cli_model=composer-2-fast`
- `cursor_cli_max_mode=true`
- `cursor_cli_config_path=~/.cursor/cli-config.json`
- `cursor_cli_sync_max_mode_before_spawn=true`

### 13.1.2 已验证事实

以下事实已在本机环境中做过真机验证，可作为第一版实现依据：

- 实际配置文件存在于：`c:\Users\Admin\.cursor\cli-config.json`
- 该文件中同时存在：
  - 顶层 `maxMode`
  - `model.maxMode`
  - `model.modelId=composer-2-fast`
- 将这两个 `maxMode` 字段临时改为 `true` 后，headless `agent` 能正常启动并完成任务
- 验证完成后，配置已恢复为原值，不依赖人工常驻修改

同时也确认了以下边界：

- `agent --help` 中没有稳定的 `--max-mode` 顶层参数
- 交互式 CLI 可使用 `/max-mode on`
- 但在无人值守 headless 场景中：
  - 初始 prompt 中写 `/max-mode on` 不会被当作真正的 slash command 执行
  - 通过 stdin 向 `agent` 写入 `/max-mode on`，也不会进入交互式命令解析器

因此，第一版应将“spawn 前同步 `cli-config.json`”视为无人值守自动化中的主方案，而不是把 slash command 当成自动化方案。

## 14. 三个任务的伪代码

### 14.1 `schedule_document_job`

```python
def schedule_document_job(document_id: str, version: int) -> None:
    snapshot = load_snapshot(document_id)
    if snapshot is None:
        log.info("snapshot missing, skip")
        return

    latest_version = snapshot["version"]
    if version != latest_version:
        log.info("stale schedule job, skip")
        return

    run_id = new_run_id()

    locked = try_acquire_runlock(
        document_id=document_id,
        run_id=run_id,
        ttl_seconds=DOC_RUNLOCK_TTL_SECONDS,
    )

    if not locked:
        mark_rerun(
            document_id=document_id,
            target_version=latest_version,
        )
        log.info("document busy, mark rerun")
        return

    enqueue_launch_cursor_run_job(
        document_id=document_id,
        version=latest_version,
        run_id=run_id,
    )
```

### 14.2 `launch_cursor_run_job`

```python
def launch_cursor_run_job(document_id: str, version: int, run_id: str) -> None:
    snapshot = load_snapshot(document_id)
    if snapshot is None:
        finalize_missing_snapshot(document_id, run_id, version)
        return

    if snapshot["version"] != version:
        finalize_stale_launch(document_id, run_id, version)
        return

    if not runlock_owned_by(document_id, run_id):
        log.warning("runlock lost, skip launch")
        return

    folder_route = resolve_folder_route(snapshot["folder_token"])
    if folder_route is None:
        finalize_failed(
            document_id=document_id,
            run_id=run_id,
            version=version,
            reason="folder_route_not_resolved",
        )
        return

    workspace = get_pipeline_workspace()

    context = build_task_context(
        snapshot=snapshot,
        run_id=run_id,
        workspace=workspace,
        folder_route=folder_route,
    )

    context_path = write_task_context_file(
        workspace_path=workspace.path,
        run_id=run_id,
        context=context,
    )

    prompt_path = write_task_prompt_file(
        workspace_path=workspace.path,
        run_id=run_id,
        context=context,
    )

    save_run_context(
        run_id=run_id,
        document_id=document_id,
        version=version,
        workspace_path=workspace.path,
        status="running",
    )

    result = cursor_launcher.launch(
        cwd=workspace.path,
        prompt_path=prompt_path,
        context_path=context_path,
        timeout_seconds=workspace.cursor_timeout_seconds,
    )

    enqueue_finalize_document_run_job(
        run_id=run_id,
        document_id=document_id,
        version=version,
        exit_code=result.exit_code,
        status=result.status,
        summary=result.summary,
    )
```

### 14.3 `finalize_document_run_job`

```python
def finalize_document_run_job(
    run_id: str,
    document_id: str,
    version: int,
    exit_code: int,
    status: str,
    summary: str | None = None,
) -> None:
    save_run_result(
        run_id=run_id,
        document_id=document_id,
        version=version,
        exit_code=exit_code,
        status=status,
        summary=summary,
    )

    clear_run_context(run_id)

    if runlock_owned_by(document_id, run_id):
        release_runlock(document_id, run_id)

    rerun = get_rerun(document_id)
    latest_snapshot = load_snapshot(document_id)

    if rerun is None or latest_snapshot is None:
        clear_rerun(document_id)
        return

    target_version = rerun["target_version"]
    latest_version = latest_snapshot["version"]

    if target_version <= version:
        clear_rerun(document_id)
        return

    if target_version != latest_version:
        target_version = latest_version

    clear_rerun(document_id)

    enqueue_schedule_document_job(
        document_id=document_id,
        version=target_version,
    )
```

## 15. 错误处理与恢复策略

第一版采用最小策略：

- webhook 解析失败：快速返回错误，不入队
- `event_seen` 写入失败：返回错误，避免无幂等继续执行
- `folder_token` 映射失败：任务失败，记录原因，不兜底乱跑
- Cursor CLI 启动失败：由 `launch` 记录失败并进入 `finalize`
- 执行器异常退出：依赖 `runlock TTL`、`snapshot TTL`、`rerun TTL` 做兜底
- 不为 v1 引入 `runlock` 续租、心跳或额外恢复守护线程

第一版不做：

- 自动重试风暴控制
- 复杂死信队列
- 巡检型恢复任务

## 16. 测试策略

第一版测试重点只覆盖高价值路径：

- 事件幂等：相同 `event_id` 只处理一次
- 文档版本淘汰：旧 `schedule` 任务不启动
- 同文档互斥：已有 `runlock` 时只写 `rerun`
- 结束后补跑：`finalize` 能重新调度最新版本
- folder 分流：`folder_token` 能命中 `qa_rule_file` 与 `dataset_id`
- 任务目录生成：`.cursor_task/{run_id}/`、`task_prompt.md`、`task_context.json`、`outputs/` 路径正确
- Cursor 注入链路：默认 agent 模式下，`task_prompt.md` 可作为初始 prompt 成功注入
- Context 读取链路：`task_prompt.md` 能明确驱动 Agent 读取 `task_context.json`
- QA 规则注入：`task_context.json` 正确写入 `qa_rule_file`，且 `task_prompt.md` 明确要求读取
- 数据集注入：`task_context.json` 正确写入 `dataset_id`，且任务单明确要求上传到该数据集
- CLI Max Mode 同步：spawn 前能正确将 `cli-config.json` 的 `maxMode` 与 `model.maxMode` 设为 `true`
- CLI Max Mode 必需性：配置文件不存在时能创建最小配置；写入失败时按失败处理，不静默降级

不优先编写低价值测试：

- 大量实现细节镜像测试
- 过度 mock 的纯搬运测试

## 17. 后续实现边界

本 spec 只定义 webhook 重构的最小可行架构。
后续实现应放在 `c:\WorkPlace\NewVLA\webhook`，并遵守以下边界：

- 旧代码只作参考，不直接搬运
- 调度层与 Cursor CLI 启动层分离
- 只维护一个统一工作区，不再按 `folder` 切分多个 workspace
- `folder_token` 只做业务分流，映射到 `qa_rule_file` 与 `dataset_id`
- `AGENTS.md` 不维护 `folder_token -> qa_rule_file` 映射；该映射只存在于运行时配置与 `task_context.json`
- Agent 不负责从仓库文档、`AGENTS.md` 或规则目录中推断 Dify 目标；`dataset_id` 必须来自 `task_context.json` 的显式注入
- 配置映射优先于运行时猜测
- 单文档尽量不并发，多文档可并发
- LLM 主输入必须是任务单，而不是机器参数堆砌
- `task_context.json` 必须由任务单显式要求读取，不假设存在隐式自动注入
- `task_prompt.md` 必须要求 Agent 先读 `task_context.json`，再读指定 QA 规则文件，最后上传到对应 `dataset_id`
- 无人值守场景中的 Max Mode 通过 spawn 前同步 `cli-config.json` 开启，不依赖交互式 slash command
