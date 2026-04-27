# Feishu App Folder Onboard Design

## 修订说明

- **2026-04-27**：`qa_rule_file` 路径合同扩展——除 `rules/...` 外，允许维护仓库内已存在的 `prompts/rules/...`（不强制为入轨再复制到 `rules/`）；真源仍存于根 `.env`。执行管线任务的**工作区**侧仍须通过初始化将模板物化到 `rules/` 或由任务层与路径约定对齐（见 §4.1、§5.3）。以下正文为现行有效表述。
- **2026-04-27（现网入轨与 §6.2/§7.3 文字关系；验收未闭环）**：目标管线里 `onboard` 的**可自动化**「先让合适的人在飞书侧能改分享」已按联调收束为：根 `.env` 必配 `FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID` 等，并仅使用 **云空间文件夹协作者** 接口 `POST .../members?type=folder`；**不**在实现中调用 §6.2 所举的 `PATCH .../public` 链式能力作为入轨主路径。正文里「企业内可见」「基础/权限初始化」「`tenant_readable` + `PATCH .../public`」等句为**成稿/产品语义与历史接口索引**，**不删不改原段**；与现网 `onboard` 不一致时，以本修订说明、[`onboard/README.md`](../../../onboard/README.md) 与代码为准。委托人在**客户端**把分享改到组织内/全员，仍属人侧步骤。与 NTH-006 的 P1/§7.3/阶段 B 门禁的**可验收表述**在验收闭环后再合并进正文（本修订在验收完成前不视为对 §6.2 的「替换落地」）。

---

## 1. 背景与目标

本设计对应 `NTH-006 飞书 App 文件夹创建与权限初始化工具`。

**与 NTH-006 的优先级对齐（避免验收争议）**：NTH 文案中的「企业内部可见」在本设计中按 **P1 尽力项** 处理——成功则与创建、`lark-cli` 一并作为「可进索引」前提；失败则进入 §7.3 部分完成态（映射可落盘，**不得**写入 `FEISHU_FOLDER_ROUTE_KEYS`），不回滚已创建文件夹。若产品将「企业内可见」升格为 **P0 门禁**，须改 §7.3：权限失败时 **禁止** 写入业务映射或须与「不入索引」策略一致，并同步修订 NTH-006 表述。

当前仓库已经明确：

- 本仓库业务链路使用的目标文件夹必须是飞书 App 文件夹
- 后续业务分流依赖 `folder_token`
- 所有配置真源统一收口到仓库根 `.env`
- 第一版抓取链路服务于“单工作区 + 单飞书应用 bot 身份”前提

这里的“单应用 bot 身份”含义是：

- 根 `.env` 中飞书侧只允许一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`
- `onboard` 创建的新 App 文件夹及其后续抓取目标，都默认应能被这同一个飞书应用 bot 身份访问
- `folder_token`、`route_key`、`dataset_id`、`qa_rule_file` 只承担业务映射职责，不承担切换飞书应用身份职责

因此，本设计的目标是提供一个人工触发的 `onboard` 初始化工具，用于：

- 调用飞书 OpenAPI 创建新的 App 文件夹
- 尝试完成基础权限初始化
- 校验业务映射输入是否满足当前合同
- 把创建结果和业务映射真源统一写入仓库根 `.env`
- 在操作者完成全部输入后，为当前工作区执行一次 `lark-cli` 初始化
- 为 `webhook`、`dify_upload`、`feishu_fetch` 提供同一份可解析真源

若后续出现“不同业务线必须绑定不同飞书应用”的需求，应视为超出本设计范围的新问题，而不是在当前合同内隐式支持。

## 2. 核心结论

### 2.1 真源口径

本设计确认以下硬约束：

- **`onboard` 执行不变量**：单次运行中，**根 `.env` 所在目录**与 `onboard` 用于解析 `qa_rule_file` 的**仓库根**须一致；与后续 `feishu_fetch` / Agent 所消费的 **执行工作区根** 须为同一物理目录（或文档化且实现可验证的等价路径映射）。`qa_rule_file` 可为仓库根下已存在的 `rules/...` **或** `prompts/rules/...` 相对路径；**不得**在目标路径不存在时通过校验。维护本仓库、仅具 `prompts/rules/` 模板时，**可直接**将 `prompts/rules/...` 写入真源，无需为入轨再复制到顶层 `rules/`；执行工作区仍须在初始化时物化到 `rules/` 供任务读取（见 §4.1、§5.3）。
- 所有真源都来自仓库根 `.env`
- 真源既包括静态基础设施配置，也包括 `folder_token` 对应的业务映射
- `folder_token -> dify_target_key + dataset_id + qa_rule_file` 的真源必须落在根 `.env`
- `webhook/config/folder_routes.example.json` 只允许作为示例文件或由根 `.env` 导出的派生产物，不再作为运行时真源

### 2.2 `onboard` 的角色

`onboard` 是人工触发的初始化工具，不属于运行时 webhook 主链路。

它的职责是：

- 询问操作者必要的业务信息
- 校验输入是否满足当前 `.env` 合同
- 自动去飞书创建 App 文件夹
- 自动把真源写回根 `.env`
- 在业务输入收集完成后，自动为当前工作区执行 `lark-cli config init`

它不负责：

- 自动推断业务线
- 自动推断 `dataset_id`
- 自动推断 `qa_rule_file`
- 自动推断 `dify_target_key`
- 在运行时替代 `webhook` 做业务分流

### 2.3 交互方式

第一版采用交互式 CLI。

也就是说：

- 人运行 `onboard`
- 工具逐项提问
- 人输入自己知道的业务信息
- 工具完成校验、飞书创建、`.env` 回写

这里“人输入”的不是“已有文件夹”，而是“准备创建的飞书 App 文件夹名称”和对应业务映射。

`lark-cli` 初始化时机也在这里一并写死：

- 不是在 `onboard` 一启动就先初始化
- 而是在操作者把本次 `onboard` 所需输入全部完成后，再进入创建、写入和初始化动作

## 3. 范围与非目标

### 3.1 本轮范围

- 创建飞书 App 文件夹
- 尝试把文件夹设为企业内可见
- 校验 `route_key`、`dify_target_key`、`dataset_id`、`qa_rule_file` 的输入合法性
- 把 `folder_token` 与业务映射写入根 `.env`
- 在当前工作区执行一次 bot-only 口径的 `lark-cli` 初始化
- 为 `webhook` 后续直接解析根 `.env` 提供稳定合同
- **可选**：生成 `webhook/config/folder_routes.example.json` 作为由根 `.env` 导出的派生示例（**第一版不强制**；未实现导出不影响本轮验收，见 §9）

### 3.2 本轮非目标

- 不把 `onboard` 接进 webhook 自动流程
- 不自动给指定用户加协作者
- 不支持批量初始化多个业务线
- 不支持按 route 切换不同飞书应用身份
- 不把 JSON 路由文件继续作为运行时真源
- 不让 Agent 或工具根据文件夹名称猜业务 key

## 4. 人机分工

### 4.1 人负责提供

以下信息只能由操作者提供：

- `route_key`
- 要创建的飞书文件夹名称
- `dify_target_key`
- `dataset_id`
- `qa_rule_file`
- 可选的父文件夹 token

**运行前准备（与 §5.3 一致）**：`qa_rule_file` 必须指向**与根 `.env` 同一仓库根**下、**已存在**的相对路径文件。允许的两种前缀：`rules/...`（执行工作区物化后的规则）或 `prompts/rules/...`（本维护仓库内模板，**不**要求为入轨再复制到 `rules/`）。禁止绝对路径与 `..` 跳目录。若执行工作区与维护仓**不同步**，初始化管线工作区时须从 `prompts/rules/` 分发到 `rules/`，或保证任务侧能解析真源中路径与本地文件一致。

原因：

- 这些字段属于业务绑定关系
- 飞书 OpenAPI 无法提供 `dataset_id`
- 工具不应推断 `qa_rule_file`
- 工具不应替操作者决定使用哪个 Dify 目标

### 4.2 工具负责自动完成

- 从根 `.env` 读取 `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 等静态配置
- 校验 `route_key` 与 `dify_target_key` 是否满足环境变量命名约束
- 校验 `dify_target_key` 是否能命中完整的 `DIFY_TARGET_<KEY>_*` 配置组
- 校验 `qa_rule_file` 是否满足 `rules/` 或 `prompts/rules/` 路径合同
- 获取 `tenant_access_token`
- 调飞书创建文件夹
- 读取返回的 `folder_token` 与 `url`
- 尝试执行企业内可见权限初始化
- 以原子方式把真源写回根 `.env`
- 在全部输入收集完成后，使用当前工作区中的 `lark-cli` 执行一次 `config init`

## 5. 根 `.env` 合同

### 5.1 设计原则

根 `.env` 现在承担两类真源：

- 静态基础设施配置
- 业务映射配置

第一版通过显式索引声明有哪些业务 key：

```env
FEISHU_FOLDER_ROUTE_KEYS=TEAM_A,TEAM_B
```

随后每个 `KEY` 对应一组展开字段。

这样做的原因：

- 解析简单
- 不依赖扫描全部环境变量名做推断
- 不需要从文件夹名称反推业务 key

### 5.2 Key 规则

`route_key` 与 `dify_target_key` 都必须满足统一的环境变量安全格式：

- 只允许大写字母、数字、下划线
- 必须匹配 `^[A-Z][A-Z0-9_]*$`
- 写入前不做隐式猜测，只允许显式输入后校验

补充说明：

- `route_key` 是 `FEISHU_FOLDER_ROUTE_KEYS` 中的业务索引键
- `dify_target_key` 是 `DIFY_TARGET_<KEY>_*` 配置组的命中键
- 两者允许不同，但都必须显式提供并独立校验

### 5.3 业务映射字段

对于每个 `KEY`，统一使用以下命名：

- `FEISHU_FOLDER_<KEY>_NAME`
- `FEISHU_FOLDER_<KEY>_TOKEN`
- `FEISHU_FOLDER_<KEY>_DIFY_TARGET_KEY`
- `FEISHU_FOLDER_<KEY>_DATASET_ID`
- `FEISHU_FOLDER_<KEY>_QA_RULE_FILE`

其中：

- `NAME` 仅用于人读和排障，不参与路由主匹配
- `TOKEN` 是飞书返回的 folder token，运行时按它做业务分流
- `DIFY_TARGET_KEY` 用于命中根 `.env` 中对应的 Dify 静态配置组
- `DATASET_ID` 是该业务线对应的知识库 ID
- `QA_RULE_FILE` 是运行时工作区内的 QA 规则文件相对路径

对 `QA_RULE_FILE` 的硬约束：

- 必须是相对路径（以仓库根为基准解析）
- 必须以 `rules/` **或** `prompts/rules/` 开头（禁止其它前缀，避免随意指向仓外路径）
- 禁止绝对路径
- 禁止包含 `..` 跳目录
- 根 `.env` 中保存的即是上述相对路径，例如 `rules/qa/folders/team_a.mdc` 或 `prompts/rules/qa/folders/team_a.mdc`
- `onboard` 写入前必须确认该相对路径在**当前仓库根**下对应文件**已存在**
- 若目标文件不存在，则直接失败，不允许只校验路径格式后写入真源
- **执行工作区**内 Agent 仍以 `rules/` 下物化结果为主要消费形态时，由工作区初始化将 `prompts/rules/` 模板分发为 `rules/...`，与 `prompts/AGENTS.txt` 等「拷入工作区」约定一致；真源中保留 `prompts/rules/...` 时，任务编排须保证路径与文件可对上（或同构维护整仓）

### 5.4 `.env` 初始化模板示例

```env
# =========================
# Feishu static config
# =========================
FEISHU_API_BASE=https://open.feishu.cn
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_REQUEST_TIMEOUT_SECONDS=60

# =========================
# Dify static config
# 这里只放静态连接信息，不放业务映射
# =========================
DIFY_TARGET_TEAM_A_API_BASE=https://dify.example.com/v1
DIFY_TARGET_TEAM_A_API_KEY=app-xxx
DIFY_TARGET_TEAM_A_HTTP_VERIFY=true
DIFY_TARGET_TEAM_A_TIMEOUT_SECONDS=60

DIFY_TARGET_TEAM_B_API_BASE=https://dify2.example.com/v1
DIFY_TARGET_TEAM_B_API_KEY=app-yyy
DIFY_TARGET_TEAM_B_HTTP_VERIFY=true
DIFY_TARGET_TEAM_B_TIMEOUT_SECONDS=60

# =========================
# Folder route index
# 所有业务映射真源入口
# =========================
FEISHU_FOLDER_ROUTE_KEYS=TEAM_A,TEAM_B

# =========================
# Route: TEAM_A
# =========================
FEISHU_FOLDER_TEAM_A_NAME=团队A知识库入口
FEISHU_FOLDER_TEAM_A_TOKEN=fldcnxxxxxxxxxxxx
FEISHU_FOLDER_TEAM_A_DIFY_TARGET_KEY=TEAM_A
FEISHU_FOLDER_TEAM_A_DATASET_ID=dataset_team_a_xxx
FEISHU_FOLDER_TEAM_A_QA_RULE_FILE=rules/qa/folders/team_a.mdc

# =========================
# Route: TEAM_B
# =========================
FEISHU_FOLDER_TEAM_B_NAME=团队B知识库入口
FEISHU_FOLDER_TEAM_B_TOKEN=fldcnyyyyyyyyyyyy
FEISHU_FOLDER_TEAM_B_DIFY_TARGET_KEY=TEAM_B
FEISHU_FOLDER_TEAM_B_DATASET_ID=dataset_team_b_yyy
FEISHU_FOLDER_TEAM_B_QA_RULE_FILE=rules/qa/folders/team_b.mdc
```

## 6. `onboard` 运行流程

### 6.1 交互输入

第一版至少询问：

- `route_key`
- `folder_name`
- `dify_target_key`
- `dataset_id`
- `qa_rule_file`
- `parent_folder_token`（可空）

在真正调用飞书前，先做本地校验：

- `route_key` 格式合法
- `dify_target_key` 格式合法
- 根 `.env` 中存在完整的 `DIFY_TARGET_<KEY>_*` 静态配置组
- `qa_rule_file` 满足 `rules/` 或 `prompts/rules/` 相对路径合同
- 当前仓库根下存在 `qa_rule_file` 指向的实际文件
- `route_key` 不与已有 route 冲突
- **`parent_folder_token` 非空时**：格式与长度符合与 `folder_token` 同类的约定（如禁止异常字符、过长输入）；**不**将飞书原始错误响应体原样打印到终端（见 §7.1）

### 6.1b 续跑与幂等

- **禁止**在「同一 `route_key` 已存在 `FEISHU_FOLDER_<KEY>_TOKEN`」且非显式「强制新建」时再次调用创建文件夹接口，以免产生孤儿云文件夹。
- 续跑语义须覆盖：仅补企业内可见、仅补 `lark-cli`、仅在两条件满足后补写 `FEISHU_FOLDER_ROUTE_KEYS` 等分支；实现可采用显式子命令或交互选项（如 `--force-new-folder`）区分「新建」与「续跑」。
- **部分激活态（双轨）**：允许 `.env` 中已存在完整 `FEISHU_FOLDER_<KEY>_*` 分组，但 `FEISHU_FOLDER_ROUTE_KEYS` **尚未**包含该 `route_key`。消费方 **不得** 仅凭存在 `FEISHU_FOLDER_<KEY>_TOKEN` 即视为路由已上线；`webhook` 仅以索引 + 分组为准（§8）。可选：`onboard` 或运维自检列出「已写映射、未入索引」的 key。

只有当这些输入都收集完成并通过本地校验后，才允许进入后续自动动作：

- 创建飞书 App 文件夹
- **阶段 A**：写回根 `.env` 中本 route 分组字段（见 §6.3，**不含** `FEISHU_FOLDER_ROUTE_KEYS`）
- 尝试企业内可见权限初始化；初始化当前工作区中的 `lark-cli`；**阶段 B**（索引追加）仅当二者均成功（见 §6.3、§7）

### 6.2 飞书侧调用

文档用语「App 文件夹」指：**由当前飞书应用、在云空间下通过开放平台「新建文件夹」能力创建的文件夹**，与官方文档中的 **create_folder** 一致；**不**指未公开的独立 API 名称。

**创建文件夹（须写死实现合同）**

1. 使用应用凭证获取 **`tenant_access_token`**（`Authorization: Bearer <tenant_access_token>`）。
2. 调用 **`POST https://open.feishu.cn/open-apis/drive/v1/files/create_folder`**（以开放平台当前文档为准），在父级为云空间根时父目录 `folder_token` 使用 **`""`** 空串等官方约定。
3. 实现须在 spec/实现说明中摘录或链接官方文档中的 **限流、日配额、不可并发创建、典型错误码**（如 `1061045`、`1062507` 等，以官方为准）供重试与排障使用。

**企业内可见（链接分享）**

4. 创建成功后，尝试将资源对企业内可读：调用开放平台 **更新云文档权限设置 / 公开权限** 类接口（如 **`PATCH .../open-apis/drive/v1/permissions/:token/public`**，具体路径与版本以官方为准），查询参数 **`type`** 须与资源类型一致（云空间文件夹/文件场景下按官方枚举选择，如 `file`，**选错会导致稳定 4xx/业务错误码**）。请求体将链接可见性设为 **`tenant_readable`**（或团队约定的 `tenant_editable`，须全文统一）。若企业策略禁止外链或返回如 `1063003` 等码，归入 §7.3 并输出补救说明。

**说明**：全文 API 路径、错误码以 [飞书开放平台](https://open.feishu.cn) 当前文档为准；实现变更时同步更新本节与验收中的可验证描述。

### 6.3 本地写入

**两阶段写入（避免 §6.4 与索引追加顺序被误读为循环依赖）**

**阶段 A — 路由分组真源（不含索引）**

**推荐顺序**：创建文件夹成功并取得 `folder_token` / `url` → **阶段 A** 持久化分组字段 → 再执行 §6.2 的公开权限设置 → 再 §6.4 `lark-cli` → 条件满足后 **阶段 B**。阶段 A 须在 `lark-cli` 之前完成，以便 §6.4 前置条件成立。

飞书创建成功并取得 `folder_token` / `url` 后，**第一次**将以下键写入根 `.env`（**不**修改 `FEISHU_FOLDER_ROUTE_KEYS`）：

- `FEISHU_FOLDER_<KEY>_NAME`
- `FEISHU_FOLDER_<KEY>_TOKEN`
- `FEISHU_FOLDER_<KEY>_DIFY_TARGET_KEY`
- `FEISHU_FOLDER_<KEY>_DATASET_ID`
- `FEISHU_FOLDER_<KEY>_QA_RULE_FILE`

下文及 §6.4 所称 **「本次 route 分组真源写入完成」** 仅指阶段 A，**不包含** 向 `FEISHU_FOLDER_ROUTE_KEYS` 追加 `route_key`。

**阶段 B — 索引追加**

仅当 **企业内可见权限初始化成功**（非 §7.3 失败态）且 **当前工作区 `lark-cli` 初始化成功** 后，**第二次**原子更新根 `.env`，将本次 `route_key` 追加到 `FEISHU_FOLDER_ROUTE_KEYS`（与已有键去重、格式合法）。§7.3 / §7.4 部分完成态下 **不得** 执行阶段 B。

**写入规则（两阶段均适用）**

- 保留未知配置行与注释
- 已存在同名键时做原位更新，不制造重复键
- 每一阶段均：**在与目标 `.env` 同目录、同卷**下创建临时文件，写入后 **`os.replace` 类原子替换**（避免跨卷 `TEMP` 导致非原子）；文本编码固定为 **UTF-8**（与仓库 PowerShell 写文件约定一致）
- 临时文件权限：**用户独占**（Unix 语义 `0600`；Windows 实现须保证仅当前用户可读写），降低多用户主机上的草稿泄露面

### 6.4 `lark-cli` 初始化

在以下条件都成立后，由 `onboard` 负责在当前工作区执行一次 `lark-cli` 初始化：

- 操作者已完成本次 `onboard` 所需全部输入
- 本地输入校验已通过
- 飞书 App 文件夹已创建成功
- 根 `.env` 已完成 **§6.3 阶段 A**（路由分组真源，**不含** `FEISHU_FOLDER_ROUTE_KEYS` 追加）

初始化动作：

1. 从根 `.env` 读取 `FEISHU_APP_ID`
2. 从根 `.env` 读取 `FEISHU_APP_SECRET`
3. 在当前工作区执行 `lark-cli config init --app-id <FEISHU_APP_ID> --app-secret-stdin`
4. 仅通过标准输入传入 `FEISHU_APP_SECRET`，不通过命令行参数明文拼接 secret
5. 紧接着执行 `lark-cli config show`（或文档规定的等价校验命令）
6. **仅**从输出中比对 **`appId`**（及明确列出的非敏感字段）；**禁止**依赖或展示含 `app_secret` 的完整配置转储；若 `show` 会打印 secret，实现须改用过滤输出或官方支持的仅元数据子命令
7. 校验 `appId` 与根 `.env` 中 `FEISHU_APP_ID` 一致后，才视为当前执行环境已配置成 bot-only 可抓取状态；随后若权限与 CLI 均成功，执行 **§6.3 阶段 B**

约束：

- 第一版只初始化当前工作区这一套 `lark-cli` 执行环境
- 不支持按 route 或单次任务切换不同飞书应用身份
- 不要求 `webhook` 在每次任务启动前重复执行 `config init`
- `feishu_fetch` 后续只消费已经初始化好的 `lark-cli` 执行环境，不接管凭证初始化

### 6.5 派生产物

`webhook/config/folder_routes.example.json` 不再作为真源。

它只允许扮演两种角色：

- 示例文件
- 从根 `.env` 导出的派生产物

因此：

- 不应要求操作者手工先改 JSON 再改 `.env`
- 不应允许运行时优先以 JSON 覆盖 `.env`

## 7. 冲突检测与错误处理

### 7.1 错误与日志策略（脱敏）

- **禁止**在标准输出、标准错误或未文档化的日志中输出：`FEISHU_APP_SECRET`、`tenant_access_token`、`DIFY_*_API_KEY`、完整 HTTP 响应体、或其它可还原凭据的片段。
- 用户可见信息：稳定错误码（或内部代号）+ 简短中文说明；需深度排障时，可写入**本地受控**调试文件（可选）并在运维文档中说明，**不**默认回显原始 API 体。
- **`folder_token` / 可访问 URL**：交互式本地终端可完整输出（与 §7.3、§7.4 补救输出一致）；CI、远程执行或日志采集场景宜写入**权限受限**工件文件或对 token/url **掩码**；文档须提示避免在录屏会议中展示完整值。

### 7.2 直接失败

以下情况直接失败，且不写入 `.env`：

- 根 `.env` 缺少 `FEISHU_APP_ID`
- 根 `.env` 缺少 `FEISHU_APP_SECRET`
- `route_key` 格式非法
- `dify_target_key` 格式非法
- 根 `.env` 中不存在完整的 `DIFY_TARGET_<KEY>_*` 配置组
- `qa_rule_file` 不满足 `rules/` 或 `prompts/rules/` 相对路径合同
- 当前仓库根下不存在 `qa_rule_file` 指向的实际文件
- 飞书创建文件夹失败
- `route_key` 已存在且对应配置与本次输入冲突
- 已存在其他 route 使用同一个 `folder_token`

### 7.3 权限初始化失败

以下情况按“创建成功但权限初始化未完成”处理：

- 文件夹创建成功
- 但企业内可见权限初始化失败

此时：

- 仍保留创建成功结果
- 仍允许把业务映射写入根 `.env`
- 不允许把 `route_key` 写入 `FEISHU_FOLDER_ROUTE_KEYS`
- 终端输出必须明确标记“权限初始化未完成”
- 必须输出 `folder_token`、`url` 和后续补救动作

这里的设计判断是：

- “企业内可见”属于初始化增强项
- 只要文件夹已成功创建，且后续目标能被当前同一个飞书应用 bot 访问，业务映射仍可视为有效
- 权限初始化失败不应回退已经成功的 folder 创建结果

### 7.4 `lark-cli` 初始化失败

以下情况按“route 已创建，但当前工作区抓取初始化未完成”处理：

- 飞书 App 文件夹创建成功
- 根 `.env` 写入成功
- 但当前工作区的 `lark-cli config init` 失败

此时：

- 应保留已创建的 `folder_token`
- 应保留已写入的根 `.env` 业务映射
- 不允许把 `route_key` 写入 `FEISHU_FOLDER_ROUTE_KEYS`
- 终端输出必须明确标记“当前工作区的 lark-cli 初始化未完成”
- 必须输出后续补救动作，例如单独补做 `lark-cli config init --app-id <FEISHU_APP_ID> --app-secret-stdin`，并再次通过 `lark-cli config show` 校验
- **建议**与 §7.3 对称：若已知，一并输出当前 `folder_token` 与文件夹 `url`，便于排障（输出方式仍受 §7.1 场景约束）

这里的设计判断是：

- `folder_token` 与 route 真源已经成立，不应因为当前工作区 CLI 初始化失败而回滚
- 但当前工作区此时不能宣称自己已具备飞书抓取能力
- 该状态与“企业内可见权限初始化失败”一样，都属于部分完成而非整体成功

### 7.5 唯一性约束

第一版至少保证以下唯一性：

- `route_key` 唯一
- `folder_token` 唯一

第一版不额外要求以下字段全局唯一：

- `dataset_id`
- `qa_rule_file`

但若实现方后续决定增加更严格约束，应以不破坏当前 `.env` 合同为前提。

**可选完整性自检（第一版不强制）**：`onboard` 启动或 CI 可校验 `FEISHU_FOLDER_ROUTE_KEYS` 中每个 key 均存在完整 `FEISHU_FOLDER_<KEY>_*` 分组，避免索引与分组长期不一致。

## 8. 与现有 spec 的联动口径

- 根 `.env` 真源与 `dify_target_key` 静态配置解析口径，以 [2026-04-26-root-env-and-dify-target-contract-design.md](./2026-04-26-root-env-and-dify-target-contract-design.md) 为准
- `webhook` 后续必须直接解析根 `.env` 中的 route 索引和 route 分组，不再把 JSON 作为运行时真源
- `webhook` 的路由结果必须显式得到 `dify_target_key`、`dataset_id`、`qa_rule_file`
- `task_context.json` 中必须显式写入 `dify_target_key`、`dataset_id`、`qa_rule_file`
- `lark-cli` 初始化职责与 `feishu_fetch` 工作区初始化口径，以 [2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](./2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 为准；但第一版执行入口由 `onboard` 承担
- 若后续实现仍存在“onboard 只产出 JSON 路由配置”或“运行时不需要 `dify_target_key`”一类旧逻辑，均应视为与本设计冲突

## 9. 验收标准

- 能基于应用身份获取 `tenant_access_token`，并调用 **`drive/v1/files/create_folder`**（或文档化且与官方一致的继任路径）创建一个新的云空间文件夹
- 创建成功后能拿到 `folder_token` 和可访问 URL
- 工具能校验 `dify_target_key` 对应的 Dify 静态配置组真实存在
- 工具能校验 `qa_rule_file` 满足 `rules/` 或 `prompts/rules/` 相对路径合同，且目标文件在**仓库根**下真实存在
- 工具能把该 `folder_token` 及对应业务映射按 **§6.3 两阶段**写回仓库根 `.env`（阶段 B 仅当权限与 `lark-cli` 均成功）
- 在 `onboard` 完成后，当前工作区能完成一次 bot-only 口径的 `lark-cli` 初始化；**可机器复核**：已安装 `lark-cli` 的**最低版本或发行说明**与本文一致，`lark-cli config init --help`（或等价）中出现 `--app-secret-stdin`，且校验步骤不依赖泄露 `app_secret` 的输出
- 只有在 **企业内可见权限初始化**（非 §7.3 失败态）与 `lark-cli` 初始化都完成后，对应 `route_key` 才进入 `FEISHU_FOLDER_ROUTE_KEYS`（与 §1 P1 默认一致；若产品改为 P0 门禁须同步修订本节）
- 根 `.env` 中存在清晰、可解析、可扩展的 folder route 真源模板
- `webhook/config/folder_routes.example.json` **不得**作为运行时真源；**是否**生成该派生文件 **不作为**第一版必达项
- **续跑**：同一 `route_key` 在已有 `FEISHU_FOLDER_<KEY>_TOKEN` 时，默认不重复创建文件夹，除非显式强制选项（§6.1b）
