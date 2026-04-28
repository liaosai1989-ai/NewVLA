# 旧实现 `.env` 与根目录新合同对照

## 修订说明

- **2026-04-28：** Webhook **文件夹 → 业务映射**真源以 `docs/superpowers/specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md` §7 为准：**优先**工作区根 `.env` 中 `FEISHU_FOLDER_ROUTE_KEYS` 与各 `FEISHU_FOLDER_<KEY>_*`；`FOLDER_ROUTES_FILE` JSON **仅** legacy 回退。下文 §1「业务映射」表仍描述分组形态；路由加载顺序以 §7 为准。
- **2026-04-28（姊妹）：** `ThirdParty.md` 已登记 webhook 运行时依赖 **`python-dotenv`**；与 §7 `.env` 解析、`ENV.mdc` 两份 `.env` 分工互补。

本文档把 `old_code/.env` 所代表的**旧 VLA 单文件配置**与当前仓库**根目录 `.env` 合同**（以 `docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md` 修订块、`onboard` 的 `env_contract`、以及 `webhook` 已声明字段为准）做归纳。**请勿将真实密钥提交进 Git**；根目录真实 `.env` 已被 `.gitignore` 忽略。

---

## 1. 真源与边界

| 项 | 说明 |
|----|------|
| 旧 | `old_code/.env` 为历史编排侧样例/遗留，**非**当前主链路真源。 |
| 新 | 仓库**根目录** `.env` 为各模块共享静态配置真源；详见证件 `AGENTS.md` 与 `env` 规则。 |
| 业务映射 | 新设计：`folder_token` → `dify_target_key` + `dataset_id` + `qa_rule_file` 落在根 `.env` 的 `FEISHU_FOLDER_*` 分组，并由 `feishu-onboard` 写回。 |

---

## 2. 旧环境变量分组（`old_code/.env` 形态）

仅按**键名**归纳用途，不复制值。

### 2.1 编排 / 队列 / 网关

- `REDIS_URL`、`VLA_HOST`、`VLA_PORT`、`VLA_QUEUE_NAME`
- `LLM_GLOBAL_MAX_INFLIGHT`、`VLA_WORKER_COUNT`
- `PUBLIC_SCHEME_HOST`（公网/隧道基址）

### 2.2 飞书 Webhook 与开放平台

- `FEISHU_WEBHOOK_PATH`、`FEISHU_API_BASE`
- `FEISHU_APP_ID`、`FEISHU_APP_SECRET`
- `FEISHU_ENCRYPT_KEY`、`FEISHU_VERIFICATION_TOKEN`
- `FEISHU_EVENT_DEDUP_TTL_SECONDS`、`FEISHU_WEBHOOK_DOC_DEBOUNCE_SECONDS`
- 文末 extra：`FEISHU_AUTO_SUBSCRIBE_DOCX*`、`FEISHU_OAUTH_*`、`FEISHU_SUBSCRIBE_FOLDER_TOKEN`、`FEISHU_USER_*`、`FEISHU_WEBHOOK_PUBLIC_URL` 等（用户态/OAuth/辅助脚本）

### 2.3 主编排 LLM（OpenAI 兼容 + Strong）

- `OPENAI_*`（base_url、key、model、temperature、max_tokens、json_retry 等）
- `VLA_MODEL_CONTEXT_TOKENS`、`VLA_AGENT_CONTEXT_BUDGET`、`VLA_TOKEN_BUDGET_PER_JOB`
- `VLA_STRONG_OPENAI_*`

### 2.4 单套 Dify（旧）

- `DIFY_API_BASE`、`DIFY_API_KEY`、`DIFY_DATASET_ID`、`DIFY_HTTP_VERIFY`

### 2.5 业务与数据路径（旧）

- `QA_PROMPT_FILE`、`FOLDER_ROUTES_FILE`（常指向 JSON 路由文件）
- `CSV_STORAGE_DIR`、`CSV_RETENTION_DAYS`、`CSV_UTF8_BOM`
- `DOC_LOCK_TTL_SECONDS`、`VLA_TOOL_USE_AGENT`、`VLA_AGENT_MAX_TURNS`

### 2.6 配置 UI 与其它

- `CONFIG_UI_HOST`、`CONFIG_UI_PORT`、`CONFIG_UI_TOKEN`
- `INTEGRATION_TEST`、`A2A_*`

---

## 3. 新环境变量分组（根 `.env` 合同要点）

### 3.1 飞书单应用（初始化层 / `onboard` 消费）

- `FEISHU_APP_ID`、`FEISHU_APP_SECRET`（全仓库**一组**；抓取侧依赖已初始化的 `lark-cli`，见 fetch spec 修订）

### 3.2 多 Dify 静态实例（按 `DIFY_TARGET_<KEY>_*`）

每组须**四项齐全且非空**（`onboard` 校验与 spec 一致）：

- `DIFY_TARGET_<KEY>_API_BASE`
- `DIFY_TARGET_<KEY>_API_KEY`
- `DIFY_TARGET_<KEY>_HTTP_VERIFY`
- `DIFY_TARGET_<KEY>_TIMEOUT_SECONDS`

**禁止**在根 `.env` 用单一 `DIFY_DATASET_ID` 作为全管线默认目标（spec 明确禁止“默认 dataset”推断）。

### 3.3 按 `route_key` 的业务映射（`onboard` 写、管线真源）

- 索引：`FEISHU_FOLDER_ROUTE_KEYS`（逗号分隔、大写 key 列表）
- 每组：`FEISHU_FOLDER_<ROUTE>_NAME`、`_TOKEN`、`_DIFY_TARGET_KEY`、`_DATASET_ID`、`_QA_RULE_FILE`
- 可选：`FEISHU_FOLDER_<ROUTE>_URL`（续跑/展示，非 `env_contract` 五键之一）

### 3.4 Webhook 执行器（`webhook` / `ExecutorSettings` 已建模）

当前代码显式从根 `.env` 加载的包括（节选，完整以 `webhook/src/webhook_cursor_executor/settings.py` 为准）：

- `REDIS_URL`、`VLA_QUEUE_NAME`
- `FEISHU_WEBHOOK_PATH`、`FEISHU_ENCRYPT_KEY`、`FEISHU_VERIFICATION_TOKEN`
- 各类 `*_TTL_SECONDS`（含 `EVENT_SEEN_TTL_SECONDS`、`DOC_SNAPSHOT_TTL_SECONDS`、`DOC_RUNLOCK_TTL_SECONDS` 等）
- `CURSOR_RUN_TIMEOUT_SECONDS`、`FOLDER_ROUTES_FILE`、`CURSOR_CLI_MODEL`、`CURSOR_CLI_CONFIG_PATH`（**勿**设已废弃的 `CURSOR_CLI_COMMAND`）

**自旧版升级（`webhook` 阻断项）：** 若曾配置 `CURSOR_CLI_COMMAND`（根 `.env` 或 K8s/系统环境变量），**必须**整行/整键删除；并保证服务账户 **PATH 可解析到 `cursor`**。否则 `ExecutorSettings` 构造失败、进程不启动。细节见 `webhook/操作手册.md`。

### 3.5 抓取链路（修订后 `feishu_fetch` 合同侧重）

- `FEISHU_REQUEST_TIMEOUT_SECONDS`；Lark 子进程在实现里固定为 `lark-cli` + `PATH`，**禁止**在根 `.env` 再写 `LARK_CLI_COMMAND`（`feishu_fetch` 在加载设置时若见该键会报错）  
- 从根 `.env` 读 `FEISHU_APP_ID`（与 `lark-cli config show` 的 `appId` 比对）等；**不**读 `FEISHU_APP_SECRET`（初始化归 `onboard` / 人工与 `lark-cli` 配置态）。

### 3.6 非根 `.env` 键

- `FEISHU_ONBOARD_REPO_ROOT`：非 editable 安装 `feishu-onboard` 时，用于指向管线仓根（进程环境变量）。

---

## 4. 迁移对照表（旧键 → 新键或去向）

| 旧（`old_code` 形态） | 新/说明 |
|------------------------|--------|
| `DIFY_API_BASE` + `DIFY_API_KEY` + 单一 `DIFY_DATASET_ID` | 拆成：某 `DIFY_TARGET_<KEY>_*` 全组 + 各 route 的 `FEISHU_FOLDER_<R>_DATASET_ID` 与 `_DIFY_TARGET_KEY` 指向该 `<KEY>`。 |
| `DIFY_HTTP_VERIFY` | 按目标实例写入对应 `DIFY_TARGET_<KEY>_HTTP_VERIFY`（**不再**全局单键）。 |
| `FOLDER_ROUTES_FILE` 指向 JSON 为真源 | **Spec 修订**要求以根 `.env` 中 `FEISHU_FOLDER_*` 为真源；**当前 `webhook` 仍从 JSON 加载路由**，与修订目标之间存在实现缺口，合并路由逻辑前需单独设计（见下节「代码审查摘要」）。 |
| `FEISHU_EVENT_DEDUP_TTL_SECONDS` | 新 `webhook` 使用 `EVENT_SEEN_TTL_SECONDS`（语义同类：事件去重/已见窗口）。 |
| `FEISHU_WEBHOOK_DOC_DEBOUNCE_SECONDS` | 新 `ExecutorSettings` 中未见同名字段；若仍需要文档去抖，须对照当前 `webhook` 实现或新增配置项。 |
| 大量 `VLA_*` / `OPENAI_*` / `CONFIG_UI_*` / `A2A_*` 等 | 属**旧编排服务**范围；新仓库中若对应模块未落地，不自动映射到根 `.env` 合同，仅在部署旧栈时保留。 |
| `QA_PROMPT_FILE` | 新链路强调按 folder 的 `FEISHU_FOLDER_*_QA_RULE_FILE`（工作区 `rules/` 相对路径）+ `task_context`；与旧单文件提示词位置不同。 |

---

## 5. 代码审查摘要（全仓库除 `old_code`）

独立代码审查已核对 `onboard`、`webhook` 与 root-env spec，结论要点：

1. **`onboard`**：`DIFY_TARGET_<KEY>_*` 四件套与 `FEISHU_FOLDER_*` 五键 + 两阶段写 `FEISHU_FOLDER_ROUTE_KEYS` 与实现一致。  
2. **`webhook`**：路由仍默认来自 `FOLDER_ROUTES_FILE` 的 **JSON**，与 spec 修订「从根 `.env` 解析 route」**未对齐**；`TaskContext` 等需贯通 `dify_target_key` 的修订在实现上仍可能不完整。  
3. 阅读 **长 spec** 时须以文首 **「修订说明」** 为准，避免正文旧段与修订矛盾。

详细分级发现（Critical / Important）已由审查代理给出，可在此后迭代中按任务拆解到各模块 issue/plan。

---

## 6. 根目录模板文件

- 可提交的占位模板：`.env.example`（与本文同目录，**无密钥**）。  
- 生产/本机真值：仅写在已被忽略的根 `.env`，从旧环境**人工**迁移并轮换泄露风险密钥。

若你只维护「管线维护仓 + onboard」，至少先备齐 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 与所涉 `DIFY_TARGET_*` 全组，再跑 `feishu-onboard` 完成 folder 与 route 写回。完整运行 webhook/RQ/编排时，再按 `webhook` 的 `settings` 与部署文档补全其余键。
