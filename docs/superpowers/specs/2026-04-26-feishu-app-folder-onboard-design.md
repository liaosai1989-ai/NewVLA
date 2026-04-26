# Feishu App Folder Onboard Design

## 1. 背景与目标

本设计对应 `NTH-006 飞书 App 文件夹创建与权限初始化工具`。

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
- 允许生成 `webhook/config/folder_routes.example.json` 作为派生示例产物

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

原因：

- 这些字段属于业务绑定关系
- 飞书 OpenAPI 无法提供 `dataset_id`
- 工具不应推断 `qa_rule_file`
- 工具不应替操作者决定使用哪个 Dify 目标

### 4.2 工具负责自动完成

- 从根 `.env` 读取 `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 等静态配置
- 校验 `route_key` 与 `dify_target_key` 是否满足环境变量命名约束
- 校验 `dify_target_key` 是否能命中完整的 `DIFY_TARGET_<KEY>_*` 配置组
- 校验 `qa_rule_file` 是否满足运行时路径合同
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

- 必须是相对路径
- 必须位于运行时工作区 `rules/` 目录下
- 禁止绝对路径
- 禁止包含 `..` 跳目录
- 根 `.env` 中保存的是运行时路径，例如 `rules/qa/folders/team_a.mdc`
- 不把 `prompts/rules/...` 这类模板资产路径直接写入业务映射真源
- `onboard` 写入前必须确认该相对路径文件已存在于当前运行时工作区
- 若目标文件不存在，则直接失败，不允许只校验路径格式后写入真源

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
- `qa_rule_file` 满足 `rules/` 相对路径合同
- 当前运行时工作区中存在 `qa_rule_file` 指向的实际文件
- `route_key` 不与已有 route 冲突

只有当这些输入都收集完成并通过本地校验后，才允许进入后续自动动作：

- 创建飞书 App 文件夹
- 写回根 `.env`
- 初始化当前工作区中的 `lark-cli`

### 6.2 飞书侧调用

最小调用链路：

1. 使用 App 身份获取 `tenant_access_token`
2. 调用创建文件夹接口
3. 记录返回的 `folder_token` 与 `url`
4. 尝试调用文件夹公开权限接口，把链接可见性设为企业内

### 6.3 本地写入

创建成功后，把以下内容写入根 `.env`：

- 写入 `FEISHU_FOLDER_<KEY>_NAME`
- 写入 `FEISHU_FOLDER_<KEY>_TOKEN`
- 写入 `FEISHU_FOLDER_<KEY>_DIFY_TARGET_KEY`
- 写入 `FEISHU_FOLDER_<KEY>_DATASET_ID`
- 写入 `FEISHU_FOLDER_<KEY>_QA_RULE_FILE`
- 仅当本次 `onboard` 的权限初始化与当前工作区 `lark-cli` 初始化都完成后，才允许把 `route_key` 追加到 `FEISHU_FOLDER_ROUTE_KEYS`

写入规则：

- 保留未知配置行与注释
- 已存在同名键时做原位更新，不制造重复键
- 先写临时文件，再原子替换原 `.env`
- 文本编码固定为 UTF-8

### 6.4 `lark-cli` 初始化

在以下条件都成立后，由 `onboard` 负责在当前工作区执行一次 `lark-cli` 初始化：

- 操作者已完成本次 `onboard` 所需全部输入
- 本地输入校验已通过
- 飞书 App 文件夹已创建成功
- 根 `.env` 已完成本次 route 真源写入

初始化动作：

1. 从根 `.env` 读取 `FEISHU_APP_ID`
2. 从根 `.env` 读取 `FEISHU_APP_SECRET`
3. 在当前工作区执行 `lark-cli config init --app-id <FEISHU_APP_ID> --app-secret-stdin`
4. 仅通过标准输入传入 `FEISHU_APP_SECRET`，不通过命令行参数明文拼接 secret
5. 紧接着执行 `lark-cli config show`
6. 校验输出中的 `appId` 与根 `.env` 中的 `FEISHU_APP_ID` 一致
7. 只有校验通过后，才视为当前执行环境已配置成 bot-only 可抓取状态

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

### 7.1 直接失败

以下情况直接失败，且不写入 `.env`：

- 根 `.env` 缺少 `FEISHU_APP_ID`
- 根 `.env` 缺少 `FEISHU_APP_SECRET`
- `route_key` 格式非法
- `dify_target_key` 格式非法
- 根 `.env` 中不存在完整的 `DIFY_TARGET_<KEY>_*` 配置组
- `qa_rule_file` 不满足 `rules/` 相对路径合同
- 当前运行时工作区中不存在 `qa_rule_file` 指向的实际文件
- 飞书创建文件夹失败
- `route_key` 已存在且对应配置与本次输入冲突
- 已存在其他 route 使用同一个 `folder_token`

### 7.2 权限初始化失败

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

### 7.3 `lark-cli` 初始化失败

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

这里的设计判断是：

- `folder_token` 与 route 真源已经成立，不应因为当前工作区 CLI 初始化失败而回滚
- 但当前工作区此时不能宣称自己已具备飞书抓取能力
- 该状态与“企业内可见权限初始化失败”一样，都属于部分完成而非整体成功

### 7.4 唯一性约束

第一版至少保证以下唯一性：

- `route_key` 唯一
- `folder_token` 唯一

第一版不额外要求以下字段全局唯一：

- `dataset_id`
- `qa_rule_file`

但若实现方后续决定增加更严格约束，应以不破坏当前 `.env` 合同为前提。

## 8. 与现有 spec 的联动口径

- 根 `.env` 真源与 `dify_target_key` 静态配置解析口径，以 [2026-04-26-root-env-and-dify-target-contract-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-root-env-and-dify-target-contract-design.md) 为准
- `webhook` 后续必须直接解析根 `.env` 中的 route 索引和 route 分组，不再把 JSON 作为运行时真源
- `webhook` 的路由结果必须显式得到 `dify_target_key`、`dataset_id`、`qa_rule_file`
- `task_context.json` 中必须显式写入 `dify_target_key`、`dataset_id`、`qa_rule_file`
- `lark-cli` 初始化职责与 `feishu_fetch` 工作区初始化口径，以 [2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 为准；但第一版执行入口由 `onboard` 承担
- 若后续实现仍存在“onboard 只产出 JSON 路由配置”或“运行时不需要 `dify_target_key`”一类旧逻辑，均应视为与本设计冲突

## 9. 验收标准

- 能基于飞书 App 身份创建一个新的飞书 App 文件夹
- 创建成功后能拿到 `folder_token` 和可访问 URL
- 工具能校验 `dify_target_key` 对应的 Dify 静态配置组真实存在
- 工具能校验 `qa_rule_file` 满足运行时 `rules/` 相对路径合同，且目标文件在当前工作区真实存在
- 工具能把该 `folder_token` 及对应业务映射写回仓库根 `.env`
- 在 `onboard` 完成后，当前工作区能完成一次 bot-only 口径的 `lark-cli` 初始化
- 只有在权限初始化与 `lark-cli` 初始化都完成后，对应 `route_key` 才进入 `FEISHU_FOLDER_ROUTE_KEYS`
- 根 `.env` 中存在清晰、可解析、可扩展的 folder route 真源模板
- `webhook/config/folder_routes.example.json` 不再被视为运行时真源
