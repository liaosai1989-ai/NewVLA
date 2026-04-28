## 修订说明

- 2026-04-28：并拢 **`run_id` 语义**，关闭 **BUG-008**。新增 **§3.1**「`run_id` 编号规则」：目录与 JSON 字段一致、**不**强制 UUID/固定前缀、生产侧每任务新发低碰撞 id、仓库提交的样例 JSON 可用稳定可读常量；§3 字段表 **run_id** 行指向 §3.1。
- 2026-04-28：**§9 Bootstrap 联动** 删 **tools junction** 默认叙事，改为 **物化物理拷贝**、**`runtime/webhook`**、**`vla_env_contract`** 与 **`bootstrap install-packages`** 安装顺序（**`vla_env_contract` 先于 `webhook`**），与 [**workspace-embedded-runtime-design**](2026-04-28-workspace-embedded-runtime-design.md) Task 0 / NTH-008 对齐。

---

# task_context、Bootstrap 样例工作区与 Agent 阅读合同

> **落地状态：已落地**（2026-04-28；实现见 `webhook/`、`dify_upload/`、`bootstrap/`、`prompts/`、`docs/superpowers/samples/`；未闭环项以 `BugList.md` 与姊妹 plan 修订说明为准。）

## 1. 背景

对 **`bootstrap` 物化后的真实执行工作区**（例如 `C:\VLA_Workplace`）做 Cursor CLI 侧评审时，需要同时满足：

- 人/代理能回答「本轮任务要做什么」；
- 与 **`feishu_fetch` / `dify_upload`** 的工具入参、环境真源不打架；
- **`task_prompt.md` 与 `AGENTS.md`** 对阅读顺序的表述可执行、无隐性冲突。

本文档把评审中已确认的结论与仍待实现的对齐点写成 **单一合同**；**本批次一次性交付**后与实现双向对齐，其后修订按维护流程与 `docedit`，**不作为**本轮拆分交付借口。

## 2. 已甄别结论（What）

### 2.1 闭环部分

| 主题 | 结论 |
|------|------|
| 任务真源 | `task_context.json` 承载 `run_id`、`document_id`、`folder_token`、`qa_rule_file`、`dataset_id`、`schema_version`、**`ingest_kind`（本期须写入）**（及 webhook 侧其它已定字段）时，与 `AGENTS.md` / `prompts/AGENTS.txt` 中「先 `task_context` → 再 `qa_rule`」一致。 |
| 自然语言入口 | `task_prompt.md` 要求必读 JSON 与 QA 规则、勿伪造工具、`dataset_id` 以 JSON 为准，可驱动代理建立正确心智。 |
| 演示规则 | `rules/sample_qa.md`（或等价路径）标明演示、不冒充生产路由，且与 `qa_rule_file` 一致时，评审价值足够。 |
| `outputs/` | **无需**在样例里预建；`write_task_bundle` 已在运行时创建 `.cursor_task/{run_id}/outputs/`。 |

### 2.2 非缺陷型「缝隙」（合同已覆盖；占位语义仍须在单次交付内闭合）

| 主题 | 结论 |
|------|------|
| `output_dir` | **刻意不写入** `task_context.json`。构造 `FeishuFetchRequest` 时 **强制**为 `{workspace_root}/.cursor_task/{run_id}/outputs`（与 [2026-04-26-webhook-cursor-executor-design.md](2026-04-26-webhook-cursor-executor-design.md) 修订说明、`prompts/AGENTS.txt` 一致）。样例 JSON 缺此键 **正确**。 |
| `ingest_kind` | **生产路径必填**：webhook 在事件解析与 `folder_token` 路由完成后 **必须** 写入 `task_context.json`（`cloud_docx` \| `drive_file`），语义对齐 `feishu_fetch.models.FeishuFetchRequest.ingest_kind`；执行侧 **只认 JSON**，构造 `FeishuFetchRequest` 时 **必须** 与其一致，不得抵触。**bootstrap 演示 JSON 亦须包含**（与 §3、§7.5、文首单次交付一致）。Redis 中旧快照缺键处理见 §7.6。 |
| Dify `api_base` / `api_key` | **不属于** `task_context`；来自 **执行工作区根** `.env`（`VLA_WORKSPACE_ROOT` 所指）及 `dify_target_key` 命中组。新人指引落在 `bootstrap/README.md`、根 env 合同 spec，而非任务 JSON。 |

### 2.3 `task_prompt.md` 与 `AGENTS.md`（已定口径）

- **`AGENTS.md` 默认已由工作区规则注入**；`task_prompt.md` 写明：**除非代理判断未加载，否则不必再打开** `AGENTS.md` 通读。
- **不**在 `task_prompt` 里强制复读 AGENTS 全文或长条款；**仍强制**先读 `task_context.json` 与 `qa_rule_file`（与 `prompts/AGENTS.txt` 顺序一致）。
- **Fallback**：若会话中确实没有主编排约束（例如裸跑 CLI、注入失败），代理应自行打开工作区根 `AGENTS.md` 补齐。
- 残余风险（资产边界等）由已注入的 `AGENTS.md` / 规则承载；本策略用「未加载则打开」兜底，而非在任务单里堆叠复述。

**占位 `dataset_id` 与干跑成功标准**

- 样例可用 `dataset_placeholder_replace_me` 等占位符；**合同**：当 `dataset_id` 匹配「已知占位模式」或任务显式 `upload_mode: none`（若未来加入）时，代理 **做到生成并校验 CSV 即视为样例成功**，**不得**对真实 Dify 发起上传。
- **`dataset_id_is_placeholder` 与干跑显式信号**：**须在本次交付内闭合**，不得延后：**要么**在 `TaskContext`/落盘 `task_context.json` 与 bootstrap 样例中写入 **`"dataset_id_is_placeholder": true|false`**（默认 `false`），**要么**在样例配套的 `task_prompt` + `sample_qa.md`（或等价）中写明与 §2.3 一致的显式干跑句——**二者至少满足其一**；推荐布尔字段以便机器与单测断言，但与「单次交付」不冲突者为先。

## 3. `task_context.json` 字段表（合同）

下列与 **`webhook_cursor_executor.models.TaskContext`** 及设计修订说明对齐；**加粗**为截至文档编写时仓库 **已合并** 的字段；*斜体*表示：**尚未合并代码**（合同可先约定）或表中 **另行写明** 之样例/占位义项。**不得**将斜体误读为「必填合同可降级省略」：凡文首「本期实现范围」或本表「必填」列已定者（含 **`ingest_kind`**、**`dify_target_key`** 合同列），语义强度 **不因实现滞后而削弱**；各行「演示可占位」等另有措辞者从其措辞。

| 字段 | 必填（生产 webhook） | 必填（bootstrap 演示） | 说明 |
|------|---------------------|------------------------|------|
| **schema_version** | 是 | 是 | 任务 JSON 模式版本。 |
| **run_id** | 是 | 是 | 与目录 `.cursor_task/{run_id}/` 末段目录名 **字面值一致**；编号义务与样例特例见 **§3.1**。 |
| **event_id** | 是 | 可用占位 | 幂等与追踪。 |
| **document_id** | 是 | 是 | 飞书文档/对象 id（与事件一致）。 |
| **folder_token** | 是 | 是 | 路由键。 |
| **event_type** | 是 | 是 | 飞书事件类型；排障与审计。**不**替代 JSON 内的 `ingest_kind`（`ingest_kind` 仍由 webhook 必填写入）。 |
| **snapshot_version** | 是 | 是 | 与快照版本对齐。 |
| **qa_rule_file** | 是 | 是 | 工作区相对路径，指向 `rules/` 下规则。 |
| **dataset_id** | 是 | 可用占位 | 运行时上传目标；占位时配合 §2.3 干跑语义。 |
| **workspace_path** | 是 | 是 | 执行工作区根绝对路径（Windows 注意规范与 JSON 转义）。 |
| **trigger_source** | 是 | 是 | 如 `feishu_webhook` / `bootstrap_sample`。 |
| **received_at** | 是 | 是 | ISO 时间字符串。 |
| **cursor_timeout_seconds** | 是 | 是 | CLI 超时 hint。 |
| *dify_target_key* | 是（合同） | 演示可占位 | 解析 `.env` 中 `DIFY_TARGET_<KEY>_*`；**当前 `TaskContext` 模型缺省，属已知缺口，实现合入后本表与 webhook 写入一并收口**。 |
| *ingest_kind* | 是 | 是 | `cloud_docx` \| `drive_file`。与 [2026-04-26-webhook-cursor-executor-design.md](2026-04-26-webhook-cursor-executor-design.md) 修订说明（2026-04-28 `task_context` 与 `feishu_fetch` 合约）一致；**本期 webhook PR 须写入快照与 `task_context`**；合并后本行应改为加粗「已存在字段」。 |
| *dataset_id_is_placeholder* | 否 | 见 §2.3（**须单次交付闭合**） | 显式干跑开关；与文案路径二选一闭合，见 §2.3。 |
| *expected_min* / *quality_checks* | 否 | 否 | 若与 `rules/qa/base/*` 对齐需要，可后续扩展；**不阻塞**当前闭环。 |

**永不写入 `task_context` 的字段（保持）**

- `output_dir`（运行时派生）
- 飞书/Dify **密钥**、长生命周期秘钥（见 env 合同 spec）

### 3.1 `run_id` 编号规则（统一合同，BUG-008）

下列四条一并阅读，避免将 **样例固定字面值** 与 **生产命名义务** 混读：

1. **结构**：执行工作区下目录 **`.cursor_task/{run_id}/`** 的末段名 **必须** 与 **`task_context.json` 内 `run_id` 字段** 为 **同一字符串**（目录 ⇄ JSON 一致）。
2. **格式**：合同 **不** 要求 `run_id` 必须为 UUID、时间戳或特定前缀（如 `run_`）；只要作为单一路径段合法、与实现/运维无冲突即可；若部署方另有内部规范，从其规范，**不**与本条矛盾即可。
3. **生产**：**webhook / 调度** 对 **每一次新任务** **应** 生成 **新发**、**低碰撞** 的 `run_id`（具体算法由实现决定，例如 UUID、带 nonce 的时间串等）。**`write_task_bundle` 等落盘代码** 以调用方传入的 `run_id` 为准，**不**代为实现发号策略。
4. **本仓库提交的 JSON 样例**（如 `docs/superpowers/samples/task_context.bootstrap.example.json` 中 `bootstrap-sample-run`）：为 **刻意稳定的可读常量**，便于文档对照与回归；**不** 表示生产环境须使用相同字形。

## 4. 与相关文档的关系

- **Webhook 主设计**：[2026-04-26-webhook-cursor-executor-design.md](2026-04-26-webhook-cursor-executor-design.md)（含 `ingest_kind` / `output_dir` 修订说明）。任务目录与 **`run_id` 字面值规则** 以 **本文 §3.1** 与 [`.cursor/rules/workplacestructure.mdc`](../../../.cursor/rules/workplacestructure.mdc) 为准，避免仅读 webhook 示例片段时误判「必须 `run_` 前缀」等。
- **Dify 与环境**：[2026-04-26-root-env-and-dify-target-contract-design.md](2026-04-26-root-env-and-dify-target-contract-design.md)、[2026-04-26-dify-upload-rebuild-design.md](2026-04-26-dify-upload-rebuild-design.md)。
- **Bootstrap 工作区结构**：[2026-04-28-production-bootstrap-deployment-design.md](2026-04-28-production-bootstrap-deployment-design.md)。
- **执行侧 AGENTS 模板**：`prompts/AGENTS.txt`（物化后为工作区 `AGENTS.md`）。

## 5. 实现与文档下一步（概要索引）

本节只保留**索引**；**可执行的改动清单与步骤**见 **§7**。代码修改 **在评审通过的单次交付 plan/PR 中一并执行**；**`ingest_kind` 贯通与 §7–§10 主线同属文首「本期实现范围」**，不得无限期停留在「仅文档」状态。

1. **`ingest_kind` 写入快照与 `TaskContext`**：**本期单次交付**见 §7.2、§7.3、§7.6；与 [2026-04-26-webhook-cursor-executor-design.md](2026-04-26-webhook-cursor-executor-design.md) 修订表一致。
2. **Webhook 路由真源（BUG-005）**：见 §7.1–§7.3（**与第 1 条同批次**，见文首）。
3. **`TaskContext` / 快照 / `dify_target_key`**：见 §7.4。
4. **`task_prompt` / `AGENTS`**：§2.3、§8、`prompts/AGENTS.txt` **全文改动清单**见 **§10**（单次交付一次合并）。
5. **bootstrap 样例**：`task_context` 样例与 §2.3 占位闭合路径、`sample_qa.md` 等见 §7.5。

## 6. Open Questions（规划阶段可消项）

**说明：** **不得**以本节搁置文首单次交付；占位策略须在交付批次内按 §2.3 **选定并闭合**。下列余项可与「是否扩展字段」迭代相关，**不**阻塞 §7–§10 主线合入。

- 占位检测：仅用布尔字段 vs 约定 `dataset_id` 前缀/后缀列表 vs 二者并存。
- `expected_min` 等质检字段是否进入 `task_context` 还是仅保留在 `rules/qa/base/*`。

---

## 7. Webhook：文件夹路由改 `.env` 真源 + `dify_target_key` 贯通（待落地实现说明）

> **用途**：回答「要改什么、怎么改」；**实现 PR** 应可逐条对照本节验收。**不**替代 [2026-04-26-webhook-cursor-executor-design.md](2026-04-26-webhook-cursor-executor-design.md) 全文，落地后在该文顶部 **修订说明** 中引用本节与 BUG-005 关单。

### 7.1 目标行为（What）

| 项 | 改前（现状） | 改后（合同） |
|----|-------------|-------------|
| folder → 业务映射真源 | `FOLDER_ROUTES_FILE` JSON 内 `folder_routes[]` | 与 `feishu-onboard` 一致：根 `.env` 中 `FEISHU_FOLDER_ROUTE_KEYS` + 每组 `FEISHU_FOLDER_<KEY>_*` |
| `dify_target_key` | JSON 路由无此字段；快照/`task_context` 无 | 每条路由必填；写入 `DocumentSnapshot`、`TaskContext`；Agent 上传时与 `DIFY_TARGET_<KEY>_*` 组配对 |
| `pipeline_workspace` | JSON 内 `path` + `cursor_timeout_seconds` | **`.env` 模式**：`path` = `VLA_WORKSPACE_ROOT`（若进程已设）的规范化绝对路径，否则 = **当前加载的 `.env` 文件所在目录**（与 `_env_file()` 父目录一致）；`cursor_timeout_seconds` = `ExecutorSettings.cursor_run_timeout_seconds`（`CURSOR_RUN_TIMEOUT_SECONDS`） |
| JSON 文件 | 运行时真源 | **仅当** `.env` 未配置 `FEISHU_FOLDER_ROUTE_KEYS`（空或缺键）时 **回退**读 `FOLDER_ROUTES_FILE`；**打日志警告**（遗留路径）；长期可删回退（另议） |

键名与分组与 `onboard/src/feishu_onboard/env_contract.py` 对齐：`FEISHU_FOLDER_<ROUTE_KEY>_TOKEN`、`…_QA_RULE_FILE`、`…_DATASET_ID`、`…_DIFY_TARGET_KEY`；`FEISHU_FOLDER_ROUTE_KEYS` 为逗号分隔、`strip`、`upper` 后的 route key 列表。

### 7.2 涉及文件与改动要点（How）

1. **`webhook/pyproject.toml`**  
   - 显式增加依赖 `python-dotenv`（若仅用 `dotenv_values` 合并 `.env` + `os.environ` 覆盖；避免手写解析）。

2. **`webhook/src/webhook_cursor_executor/settings.py`**  
   - `FolderRoute`：增加 `dify_target_key: str = "DEFAULT"`（**JSON 回退**时旧文件无该字段仍可反序列化；**`.env` 模式**须四字段齐全否则 `ValueError`）。  
   - 新增：从 `_env_file()` 读入并与 `os.environ` 中 `FEISHU_FOLDER_*` / `FEISHU_FOLDER_ROUTE_KEYS` 合并（进程环境覆盖文件）。  
   - 新增：`load_routing_config` 分支——若 `FEISHU_FOLDER_ROUTE_KEYS` 非空 → 构造 `RoutingConfig`（`pipeline_workspace` 按 §7.1）；否则 → 现有 `json.loads(folder_routes_file)` 路径 + `warning`。  
   - **不要**对 `get_executor_settings` 的 `lru_cache` 行为引入隐式缓存错误：若路由依赖仅 `.env` 文件内容，确保与现有 `ExecutorSettings` 加载同一 `.env` 路径。

3. **`webhook/src/webhook_cursor_executor/state_store.py`**  
   - 快照读写路径与 Pydantic 校验变更时，与 §7.6 **Redis 旧数据**策略一致（缺 `ingest_kind` / `dify_target_key` 时拒绝任务 vs 默认值 vs 运维清库须在实现 PR 写清）。

4. **`webhook/src/webhook_cursor_executor/feishu_folder_resolve.py`**（或当前承担 `resolve_folder_route` 的模块）  
   - `FolderRoute` 增字段后，命中与错误消息全覆盖；测试见 §7.6 枚举。

5. **`webhook/src/webhook_cursor_executor/models.py`**  
   - `DocumentSnapshot`：增加 `dify_target_key: str = "DEFAULT"`（默认兼容 Redis 中旧 JSON 快照缺键）；**`ingest_kind`**：实现策略与 §7.6 一致（推荐 **无默认**、新快照必填写入；仅当合同允许旧键时用默认或拒绝加载）。  
   - `TaskContext`：增加 `dify_target_key: str` 与 **`ingest_kind: str`**（生产路径由快照写入，与 §2.2、§3 **必填** 一致）。

6. **`webhook/src/webhook_cursor_executor/app.py`**  
   - 构造 `DocumentSnapshot` 时增加 `dify_target_key=route.dify_target_key`；**`ingest_kind`** 在解析完成后写入快照（与 §2.2 必填一致）。

7. **`webhook/src/webhook_cursor_executor/worker.py`**  
   - `ingest_feishu_document_event_entry` 内构造 `DocumentSnapshot` 同样传入 `route.dify_target_key` 与 **`ingest_kind`**。  
   - **RQ 契约**：HTTP 在入队 **`ingest_feishu_document_event`** 时 **须传入 `ingest_kind`**（与 `app.py` 侧在具备完整 `event` 字典时算出的值一致）；**禁止**依赖 worker 仅凭 `document_id` + `event_type` 可靠反推（边界情况易与 `feishu_fetch` 的 `cloud_docx` / `drive_file` 配对要求冲突）。若实现另选等价物（例如序列化最小 `event` 片段），须在实现 PR 与 `webhook/操作手册.md` 写清。

8. **`webhook/src/webhook_cursor_executor/scheduler.py`**  
   - `TaskContext(...)` 增加 `dify_target_key=snapshot.dify_target_key`、`ingest_kind=snapshot.ingest_kind`。

9. **`webhook/src/webhook_cursor_executor/task_files.py`（**须**，单次交付范围）**  
   - `build_task_prompt` 增加一句：`dify_target_key` 以 `task_context.json` 为准，与 `.env` 中 `DIFY_TARGET_<KEY>_*` 解析上传端点；**`ingest_kind`** 以 `task_context.json` 为准。

10. **`prompts/AGENTS.txt`** — **全文以 §10  checklist 为准**，本节不重复列句。

11. **测试 `webhook/tests/`（完整枚举，避免漏改）**  
   - `test_settings.py`：`.env` 路由与 JSON 回退（见上）。  
   - `test_feishu_folder_resolve.py`：路由形状含 `dify_target_key` 后仍命中/失败语义正确。  
   - `test_app.py`、`test_worker_ingest.py`：凡构造 `FolderRoute` / `DocumentSnapshot` 处补 **`dify_target_key`、`ingest_kind`**（或依赖合同允许的默认）。  
   - `test_state_store.py`：`DocumentSnapshot` 序列化/反序列化与 §7.6 缺键策略一致。  
   - `test_scheduler.py`：落盘 `task_context.json` 断言含 **`dify_target_key`、`ingest_kind`**。  
   - `test_task_files.py`、`test_cursor_cli.py`：随 `task_prompt` / 合同变更按需更新。  
   - 全量 `cd webhook; pytest` 绿。

12. **文档与登记**  
    - `webhook/操作手册.md`：第四步改为「优先配置 `.env` 中 `FEISHU_FOLDER_ROUTE_KEYS` 与各 route 组；`FOLDER_ROUTES_FILE` 仅遗留回退」。  
    - `webhook/阶段性验收手册.md`：验收「路由命中」以 `.env` 为准；JSON 双写说明删除或降级为回退说明。  
    - `.env.example`：强调生产路径；`FOLDER_ROUTES_FILE` 注释为可选遗留。  
    - `BugList.md` **BUG-004 / BUG-005**：关单条件与验证方式（实现合入后由负责人更新状态）。  
    - [2026-04-26-webhook-cursor-executor-design.md](2026-04-26-webhook-cursor-executor-design.md)：落地后 **修订说明** 一条指向本节与实现 PR。

### 7.3 验收标准（实现 PR 自检）

- 设 `FEISHU_FOLDER_ROUTE_KEYS` 与非空各键时：**不依赖** JSON 即可 `resolve_folder_route` 与落盘快照。  
- 快照与 `task_context.json` 均含 **`dify_target_key`**，且与 `.env` 中该 route 的 `FEISHU_FOLDER_*_DIFY_TARGET_KEY` 一致。  
- 快照与 `task_context.json` 均含 **`ingest_kind`**（`cloud_docx` \| `drive_file`），与 webhook 事件解析结果一致；§7.6 旧 Redis 策略已文档化。  
- `pipeline_workspace.path` 与 `VLA_WORKSPACE_ROOT`（或 `.env` 父目录）一致，**消除**与 JSON `pipeline_workspace.path` 强制双写（回退 JSON 模式除外）。  
- 未设 `FEISHU_FOLDER_ROUTE_KEYS` 时：行为与改前一致（JSON），且日志含遗留警告。

### 7.4 与 §3 字段表的关系

§3 中 *dify_target_key* 行在 §7 落地后改为 **代码已存在字段**；并同步更新 `2026-04-28-task-context-bootstrap-sample-agent-contract-design.md` 文首落地状态（或与 webhook spec 成对更新，遵守 `docedit`）。

### 7.5 Bootstrap 样例（与路由无关的提醒）

物化样例工作区的 `task_context` **演示 JSON** **须**含 **`ingest_kind`**（`cloud_docx` \| `drive_file`）与占位 **`dify_target_key`**（如 `DEFAULT`），**与 §3「必填（bootstrap 演示）」列一致，不得弱化**；并与 `.env.example` 中 `DIFY_TARGET_DEFAULT_*` 注释对应，便于端到端理解与 `feishu_fetch` 示例一致。

### 7.6 Redis、遗留快照、示例路由 JSON、onboard、CI（实现 PR 必须对照）

| 主题 | 合同 |
|------|------|
| **Redis / `state_store`** | `DocumentSnapshot.model_validate_json` 加载旧数据时，若缺 **`ingest_kind`** 或 **`dify_target_key`**：实现 PR **须**选定其一并写进运维说明——（a）拒绝本次 run 并记可观测原因；（b）对 `dify_target_key` 等允许 Pydantic 默认、对 `ingest_kind` **不**默认而拒绝；（c）要求清 Redis / 升快照版本。禁止「静默用错 ingest 路径」。 |
| **`webhook/config/folder_routes.example.json`** | **遗留 JSON 回退** 模式下的示例：每条 `folder_routes[]` **须**含与 `FolderRoute` 合同一致的字段（含 **`dify_target_key`**），避免复制粘贴缺键；真源仍以 `.env` 为优先（§7.1）。 |
| **onboard** | `onboard/src/feishu_onboard/env_contract.py` 与 `webhook` 解析用的键名、分组、大小写规则（如 `FEISHU_FOLDER_ROUTE_KEYS`、`FEISHU_FOLDER_<KEY>_*`）**须**一致；实现 PR 合并前做一次 **对照验收**（或单测共享常量），避免「入轨写入 / webhook 读取」漂移。 |
| **CI / 手测矩阵** | 本仓库若无集中 CI workflow，实现 PR **仍须**至少：`cd webhook && pytest` 全绿；改动触及 **`dify_upload` / §8 封装 / `bootstrap`** 时，同批次对相关包执行 `pytest`。后续若引入根级 CI，**推荐**矩阵覆盖 `webhook`、`bootstrap`、`dify_upload`、`feishu_fetch`（与变更范围一致）。 |
| **`feishu_fetch` 文档** | `feishu_fetch/README.md` 等须标明：生产侧 `ingest_kind` **真源**为 `task_context.json`（webhook 写入），`FeishuFetchRequest.ingest_kind` **必须**与其一致。 |

## 8. Dify 上传：薄封装优先（已定策略）

> **原则**：闭环靠 **机器拼 `DifyTargetConfig`**；`prompts/AGENTS.txt`（工作区 `AGENTS.md`）只写 **禁令 + 指向封装**，不把 `DIFY_TARGET_<KEY>_*` 拼接细节托付给模型。

### 8.1 理由（简述）

- 模型对 `dataset_id` 敏感、对 `api_base` / `api_key` 组键 **不敏感** → 纯文档补全 **复发率高、占 token**。
- 根 `.env` 已是 `DIFY_TARGET_<KEY>_*` + folder 映射形态 → **本该代码拼**，不该每任务让模型拼。
- 封装 **可单测**、键名变更 **改一处**；长文 AGENTS 做不到。

### 8.2 落地形态（**单次交付须实现**）

- **解析**：在本仓（与 `dify_upload` 同仓或邻包）提供例如 `resolve_dify_target(task_context, env_path) -> DifyTargetConfig`：读 `task_context` 内 `dify_target_key`、`dataset_id`；从 **同一工作区根** `.env` 读 `DIFY_TARGET_<KEY>_*`（路由真源仅在 `.env` 时，封装与 webhook 共用同一套键名约定）。
- **调用**：代理侧形如：`upload_csv_to_dify(resolve_…(…), csv_path)`（或等价一步：解析结果传入现有 `dify_upload` API）。
- **AGENTS.md**：上传禁令 + 封装指针的 **具体措辞与条数** 见 **§10 表行 3～4**（保持短文，不展开 env 组键）。

### 8.3 何时仅补 AGENTS + `task_prompt`（**非本批次交付路径**）

- **本批次**：以 **§8.2 代码合入** 为准；**不得**援引本条推迟 §8.2。
- **其它场景**（例如短期上不了代码、硬性「工作区零 Python 新增」）：可 **临时**步骤清单 + 环境变量表，须标 **过渡**；**长期仍须**收敛到 §8.2 封装。

### 8.4 与 `dify_upload` 边界

- `dify_upload` **继续**不读 `task_context.json`；**封装**负责读 task_context + `.env` → 产出 `DifyTargetConfig` → 再调 `dify_upload`。与本仓现有「调用方组装」合同一致，只是调用方从「裸模型」收束为「唯一解析函数」。

## 9. Bootstrap 联动（与 §7 / §8 **同批次**）

> **结论**：不推翻 `materialize` / `install-packages` 主流程；须同步 **种子与运维说明**、**`doctor` 门禁**、**生产 bootstrap 设计文**。与 [2026-04-28-production-bootstrap-deployment-design.md](2026-04-28-production-bootstrap-deployment-design.md) 成对修订时遵守 `docedit`。**内嵌 runtime** 物化与目录语义以 [**workspace-embedded-runtime-design**](2026-04-28-workspace-embedded-runtime-design.md) **§3–§4**（**`runtime/webhook`**、**`vla_env_contract`**、**实拷贝 `tools/*`**）为准；**非**以 tools **junction** 为默认。

| 范围 | 是否改 bootstrap 代码 | 内容 |
|------|----------------------|------|
| **物化主链路** | 否（通常） | `materialize-workspace`：**递归物理拷贝** **`webhook`→`runtime/webhook`**、**`vla_env_contract`**、**`tools/dify_*`**（见 **workspace-embedded** §3）；**`AGENTS`/`rules` 分发**、工作区 `.env` 种子；**不依赖** webhook 用 JSON 还是 `.env` 做 folder 路由。 |
| **`.env` 种子与 README** | 文案/示例 | `.env.example`、物化交接说明：写明生产 **优先** `FEISHU_FOLDER_ROUTE_KEYS` + 各 `FEISHU_FOLDER_<KEY>_*`；`FOLDER_ROUTES_FILE` **仅**遗留/回退。`bootstrap/README.md` 中 **BUG-005「JSON 与 `--workspace` 双写」** 在 webhook §7 收口后 **必须**改为新口径，避免误导。 |
| **`doctor`** | 是 | 现依赖 `FOLDER_ROUTES_FILE` 可读性做 WARNING。§7 落地后 **增加**对 `FEISHU_FOLDER_ROUTE_KEYS` 与各 route 组键完整性的检查；JSON 路径 **仅**在「未配置 ROUTE_KEYS、走 legacy」时保留原逻辑。 |
| **生产 bootstrap 设计 / plan** | 修订说明 | `2026-04-28-production-bootstrap-deployment-design.md` §3.2 等处「`pipeline_workspace.path` 以 JSON 为准」——BUG-005 关单后 **追加修订说明**：与 `VLA_WORKSPACE_ROOT` / 工作区 `.env` 父目录、`CURSOR_RUN_TIMEOUT_SECONDS` 对齐（以 webhook 实现为准）。 |
| **薄封装 §8 落点** | 视包而定 | 封装若在 **`dify_upload` 包内**：在 **`tools/dify_upload`** 源码树内扩展模块即可。若 **新建 Python 包**：须纳入 **`bootstrap` `install-packages`** 可编辑目录集合（与 **`dify_upload`** 同类），安装顺序见 **workspace-embedded** §4.1（**`vla_env_contract` 先于依赖方**）。 |
| **`prompts/AGENTS.txt`** | 否（bootstrap 侧） | **模板条文真源：§10 checklist**（§2.3 / §8 等均汇入该节，单一出处）；bootstrap **只负责物化**，不得在仓库侧另写一套削弱 §10 语义的编排说明。 |

**验收（与本 spec 单次交付同批次）**：`doctor --workspace` 在「仅 `.env` 路由、无 JSON」配置下行为符合文档；README / `.env.example` 与 §7 真源一致；生产 design 文首或修订说明与实现同步。

## 10. `prompts/AGENTS.txt` 改动汇总（一处对照、**单次交付一次合并**）

> 下列为 **本文档涉及的全部** `AGENTS.txt` 拟定增量/修订；实现时 **勿**在 §2 / §7 / §8 多处各改一版，**以本节为 checklist** **与同批次 §8.2 一并**合并进模板。若 §8.2 模块名收口稍晚于模板首 commit，可先 **占位** 字符串，**须在同一批次内**替换为 **真实 import 路径或 CLI 子命令名**，不得拆 PR 遗留占位。

| # | 位置（建议锚定现有小节） | 改动内容 |
|---|-------------------------|----------|
| 1 | **文件定位** 或 **先读什么** 之前，短段「会话与 `AGENTS.md`」 | 写明：工作区规则/会话通常会注入本文件对应内容；**若判断未加载**主编排约束，须**打开工作区根 `AGENTS.md` 通读**。与 §2.3、`task_files.build_task_prompt` 口径一致（不弱化「先 task_context → 再 qa_rule」）。 |
| 2 | **先读什么** →「其中」列表 | 在 `dataset_id` 条 **同层** 增加：`dify_target_key`（及将来 webhook 写入的其它业务字段）**仅**从 `task_context.json` 读取；**不得**从静态 `rules/` 或仓库文档反推 Dify 实例。 |
| 3 | **主职责** 第 6 步或 **主流程原则** 上传相关条 | **上传 Dify** 须通过 **§8 薄封装**（如 `resolve_dify_target` + `dify_upload`）：**禁止**仅凭 `dataset_id` 臆造 `api_base` / `api_key`；**禁止**手拼环境变量组键。用 **2～3 行**写清：唯一入口模块/函数名 + 「不准手拼」。 |
| 4 | **运行合同 `.env`** 小节 | 补一句：`DIFY_TARGET_<KEY>_*` **静态组**由执行工作区根 `.env` 提供；与 `task_context` 中的 `dify_target_key`、`dataset_id` **配对使用**，配对逻辑 **只走 §8 封装**，不由模型现场发明键名。 |
| 5 | **主流程原则**（**须**，与 §2.3 占位符一致） | 若 `task_context` / 规则标明 **占位 `dataset_id` 或干跑**：只做到生成并校验 CSV，**不对**真实 Dify 环境发起上传。 |

**落地后**：物化工作区 `AGENTS.md` 与本文同步；根 `AGENTS.md`（维护仓说明）若引用执行侧模板，链到 `prompts/AGENTS.txt` 即可，**避免**两处各写一套上传细则。

**不包含在本节、由别文件维护的**：`task_prompt.md` 由 `webhook_cursor_executor/task_files.build_task_prompt` 生成——与 §2.3 对齐时改 Python 模板，**不**重复粘贴进 `AGENTS.txt`。
