# Root Env And Dify Target Contract Design

> **落地状态：已落地（主路径）**（2026-04-28；与 `.cursor/rules/env.mdc` 及三模块 settings 一致；路由真源与 JSON 派生产物待对齐见 `BugList.md` BUG-005。）

## 修订说明（2026-04-30 `feishu_fetch` 与 `lark-cli`：PATH 固定命令名；废键 `LARK_CLI_COMMAND`；BUG-001）

本文件以下正文保留原文。若与 **2026-04-27 onboard-lark-cli 联动补充** 或正文 **§4.3 / §9.2** 等仍写「`feishu_fetch` 消费 `LARK_CLI_COMMAND`」「检查 `LARK_CLI_COMMAND` 可执行」「缺 `FEISHU_APP_SECRET`」等冲突，**以本段为准**（对齐仓库 `feishu_fetch/src/feishu_fetch/config.py`、`facade.py`）：

- **`feishu_fetch` 根 `.env` 合同**：**不**包含 **`LARK_CLI_COMMAND`**；该键若存在则 **加载设置阶段 `ValueError`**（须整行删除）。
- **子进程**：固定命令名 **`lark-cli`**，**仅**经 **`shutil.which`** 解析；**非**用户可配可执行路径。另只读 **`FEISHU_REQUEST_TIMEOUT_SECONDS`**、**`FEISHU_APP_ID`**（等与当前实现一致的键）；**不**读 **`FEISHU_APP_SECRET`** 作运行时注入。
- **运行时职责**：在已初始化之 `lark-cli` 配置前提下，**校验** PATH 上 **`lark-cli`** 可、`config show` 等预检通过后执行抓取；**非**「核对某 `LARK_CLI_COMMAND` 环境变量」。
- **§9.2 历史条目**：「`LARK_CLI_COMMAND` 不存在」应理解为 **`lark-cli` 在 PATH 上不可解析**；「缺 `FEISHU_APP_SECRET`」与当前 `feishu_fetch` 模块合同**不一致**者以 **`feishu_fetch` 包 README / feishu-fetch-lark-cli spec 文首修订**为准。

## 修订说明（2026-04-27 MarkItDown 固定依赖口径补充）

本文件以下正文保留原文，不直接改写原设计内容。

针对本轮评审已确认“新代码继续使用 `MarkItDown`，但不再暴露 `MARKITDOWN_COMMAND` 配置项”这一口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- 第一版中，`feishu_fetch` 的转换实现仍固定使用 `MarkItDown`
- `MarkItDown` 属于实现依赖，不属于根 `.env` 对 `feishu_fetch` 暴露的配置合同
- `MARKITDOWN_COMMAND` 不再作为根 `.env` 配置项传入新代码，也不应继续出现在 settings/dataclass、README、测试样例和对外合同中
- 若正文旧表述仍把 `MARKITDOWN_COMMAND` 列为 `feishu_fetch` 的根 `.env` 配置项，应按本修订说明覆盖理解

## 修订说明（2026-04-27 onboard-lark-cli 联动补充）

本文件以下正文保留原文，不直接改写原设计内容。

针对 `onboard` 当前正文已确认承担 `lark-cli` 初始化职责这一新口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- 第一版中，根 `.env` 中唯一一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 的直接消费 owner 不再是 `feishu_fetch`，而是 `onboard` 所承担的“工作区初始化层”
- `onboard` 在操作者完成本次初始化所需全部输入、且本地校验通过后，负责读取根 `.env` 中的 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，并在当前工作区执行 `lark-cli config init`
- `feishu_fetch` 不再把 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`MARKITDOWN_COMMAND` 视为自己的模块合同；`feishu_fetch` 只消费 `LARK_CLI_COMMAND`、`FEISHU_REQUEST_TIMEOUT_SECONDS` 以及“已初始化好的 `lark-cli` 执行环境”
- `feishu_fetch` 在运行时的职责只包括：检查 `LARK_CLI_COMMAND` 可执行、检查当前执行环境中的 `lark-cli` 已完成初始化、然后执行正文抓取；不负责首次初始化 `lark-cli`
- `webhook` 不负责在每次任务启动前重新执行 `lark-cli config init`，也不负责给 `feishu_fetch` 注入飞书凭证来替代工作区初始化
- Feishu 抓取链路应拆成两个阶段理解：
  - 初始化阶段：`onboard -> 读取根 .env 中 FEISHU_APP_ID / FEISHU_APP_SECRET -> 执行 lark-cli config init -> 产出当前工作区可抓取状态`
  - 任务阶段：`task_context / tool input -> feishu_fetch 检查 lark-cli 可执行与已初始化状态 -> 执行正文抓取`
- 若正文中仍出现“`feishu_fetch` 直接读取 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 完成抓取”“`feishu_fetch` 缺 app 凭证即 fail fast”或同类旧表述，均按本修订说明覆盖理解
- 若正文中仍出现“`folder_token -> dataset_id + qa_rule_file` 业务映射不应写入根 `.env`”或“这层业务映射应留在 `webhook` 路由配置”一类旧表述，均继续以上方修订说明和 `onboard` 当前正文为准
- 相关联动口径以 [2026-04-26-feishu-app-folder-onboard-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md) 与 [2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 的当前正文为准

## 修订说明（2026-04-27 评审收口）

本文件以下正文保留原文，不直接改写原设计内容。

针对本轮评审与 `onboard` 当前正文口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- 根 `.env` 不只承载静态基础设施配置，也承载 `folder_token -> dify_target_key + dataset_id + qa_rule_file` 的业务映射真源
- `webhook/config/folder_routes.example.json` 不再作为运行时真源，只能作为示例文件或由根 `.env` 导出的派生产物
- `webhook` 后续对 route 的解析输入，必须直接来自根 `.env` 中的显式 route 索引和 route 分组，而不是独立 JSON 真源
- `task_context.json` 与 `webhook` 路由结果，必须显式包含 `dify_target_key`、`dataset_id`、`qa_rule_file`
- 根 `.env` 中的 `FEISHU_FOLDER_<KEY>_QA_RULE_FILE` 必须保存运行时工作区 `rules/` 目录下的相对路径，例如 `rules/qa/folders/team_a.mdc`
- 不应直接把 `prompts/rules/...` 这类模板资产路径写入业务映射真源
- `route_key` 与 `dify_target_key` 都必须满足环境变量安全格式 `^[A-Z][A-Z0-9_]*$`
- `onboard` 在写入根 `.env` 前，必须先校验 `dify_target_key` 能命中完整的 `DIFY_TARGET_<KEY>_*` 静态配置组，并校验 `qa_rule_file` 满足 `rules/` 相对路径合同
- 根 `.env` 中飞书侧只允许一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 作为当前工作区初始化来源；当前链路不支持按 route 或任务切换飞书应用身份
- 若正文中仍出现“这层业务映射应留在 webhook 路由配置，不放进根 `.env`”或同类旧表述，均按本修订说明覆盖理解

## 修订说明（2026-04-26 NTH-006 联动补充）

本文件以下正文保留原文，不直接改写原设计内容。

针对 `NTH-006 飞书 App 文件夹创建与权限初始化工具`，现补充以下修订口径；若与正文旧表述冲突，以本修订说明为准：

- 根 `.env` 不再只承载静态基础设施配置，也承载 `folder_token -> dify_target_key + dataset_id + qa_rule_file` 的业务映射真源
- `webhook/config/folder_routes.example.json` 不再是业务映射真源，只能作为示例文件或由根 `.env` 派生出的产物
- `onboard` 的职责是创建飞书 App 文件夹，并把 `folder_token` 与对应业务映射直接写回根 `.env`
- 推荐的根 `.env` 业务映射模板与字段命名，以 [2026-04-26-feishu-app-folder-onboard-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md) 为准
- 根 `.env` 中飞书侧只允许一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 作为当前工作区初始化来源，不支持按 route、`folder_token` 或单次任务切换不同飞书应用
- 所有进入当前抓取链路的目标文档，必须事先对这同一个飞书应用 bot 身份可访问；业务映射字段只负责路由，不负责选择飞书应用身份
- 若正文中仍出现“业务映射应留在 webhook 路由配置，不放进根 `.env`”等旧表述，均按本修订说明覆盖理解

## 修订说明

本次修订只做合同收口，不扩展实现设计，目标是让该文档可以直接作为跨模块边界约束使用：

- 补齐 `dify_target_key + dataset_id` 必须运行时显式传入的统一口径
- 明确根 `.env` 中多套 Dify 静态配置的唯一命名规则
- 删除模块内部类名、函数名、文件布局等实现级约束
- 删除与 `feishu_fetch` 独立 spec 重叠的实现描述
- 补齐 `task_context.json`、`qa_rule_file`、错误口径、成功标准的最小可校验要求
- 明确 `old_code/` 下旧 `.env` 仅作历史参照，当前主链路只认仓库根目录 `.env`

## 1. 背景与目标

本设计用于同时收口三个待优化点：

- `NTH-002 webhook 补齐 Dify 目标配置合同`
- `NTH-004 根目录 .env 与各模块配置消费合同收口`
- `NTH-005 飞书文件夹-Dify 知识库-QA 合同一对一映射收口`

当前仓库根目录 `.env` 已按模块分组整理，但实际消费合同还不统一：

- `webhook` 已直接读取根 `.env`
- `dify_upload` 当前更偏“显式传入完整目标配置”
- `feishu_fetch` 还没有正式落地根 `.env` 读取口径
- Dify 侧 `dataset_id`、`api_base`、`api_key` 的责任边界仍容易混淆

本设计的目标不是新增中间抽象层，而是把当前仓库的最小真实口径写死：

- 根 `.env` 是各模块共享的静态配置源
- 各模块直接读取自己负责的那组根 `.env` 配置
- LLM / `task_context.json` 只承载业务运行时参数，不承载基础设施静态配置
- Dify 的 `dify_target_key` 与 `dataset_id` 必须运行时显式传入，根 `.env` 不允许提供默认值

本设计只收口输入输出合同、配置边界与错误口径；不引入新的公共抽象，不冻结模块内部实现结构。

## 2. 已定原则

### 2.1 根 `.env` 是统一静态配置源

当前仓库内：

- `webhook`
- `dify_upload`
- `feishu_fetch`

都允许直接读取仓库根 `.env`。

这里的“允许”不是无边界乱读，而是：

- 每个模块只读取自己负责的配置分组
- 不跨模块偷读对方配置
- 不把路由、业务目标、临时任务参数重新塞回 `.env`

### 2.2 LLM 不注入基础设施配置

LLM 或运行时任务单不应注入：

- `api_base`
- `api_key`
- `app_secret`
- 命令路径
- 默认超时

这些都属于静态基础设施配置，应由模块从根 `.env` 自己读取。

LLM / 运行时合同只承载业务参数，例如：

- `dataset_id`
- `document_id`
- `file_token`
- `output_dir`
- `qa_rule_file`

### 2.3 `dify_target_key` 与 `dataset_id` 必须运行时显式传入

`dify_target_key` 与 `dataset_id` 都不属于静态基础设施配置，而属于本次任务的业务目标引用。

因此：

- `dify_target_key` 必须由运行时显式传入
- `dataset_id` 必须由运行时显式传入
- 根 `.env` 禁止提供默认 `DIFY_DATASET_ID`
- 不允许靠模块内部兜底默认值决定上传目标
- 不允许只给 `dataset_id` 而不说明它属于哪一套 Dify 实例

这是为了避免：

- 不同 `folder_token` 或不同任务误传到同一个默认数据集或默认实例
- 看似“能跑”，实际目标漂移
- 调试阶段默认值进入正式链路

## 3. 非目标

- 不新增独立顶层 resolver 包
- 不引入新的配置中心
- 不让 `webhook` 代替其他模块读取全部配置
- 不让 LLM 承担密钥和静态连接参数注入
- 不在本轮处理 legacy Feishu 配置下线，只明确其边界
- 不在本 spec 定义模块内部类名、函数名、文件名
- 不在本轮兼容旧的单实例 Dify 环境变量命名
- 不提供默认 Dify 目标推断，也不做自动迁移逻辑

## 4. 配置责任矩阵

### 4.1 `webhook`

`webhook` 继续直接读取自己的根 `.env` 配置，例如：

- `REDIS_URL`
- `VLA_QUEUE_NAME`
- `FEISHU_WEBHOOK_PATH`
- `FEISHU_ENCRYPT_KEY`
- `FEISHU_VERIFICATION_TOKEN`
- `CURSOR_*`
- 各类 TTL 与路由文件位置

`webhook` 的新增硬约束：

- 必须把 `dify_target_key` 与 `dataset_id` 作为运行时显式字段写入 `task_context.json`
- 不向任务上下文注入 `api_base`、`api_key`
- 不靠根 `.env` 的默认 `DIFY_DATASET_ID` 推断目标
- 不允许只注入 `dataset_id` 而不注入 `dify_target_key`

### 4.2 `dify_upload`

`dify_upload` 直接读取自己的根 `.env` 配置，例如：

- `DIFY_TARGET_<KEY>_API_BASE`
- `DIFY_TARGET_<KEY>_API_KEY`
- `DIFY_TARGET_<KEY>_HTTP_VERIFY`
- `DIFY_TARGET_<KEY>_TIMEOUT_SECONDS`

`dify_upload` 不应从根 `.env` 读取默认 `dataset_id`。

该模块的合同应改为：

- 静态 Dify 连接配置由模块自己从根 `.env` 读取
- `dify_target_key` 与 `dataset_id` 都必须由调用方显式传入
- 模块内部再把“运行时 `dify_target_key` + `dataset_id` + 根 `.env` 中命中的静态配置”合成为最终上传目标

这里的“调用方”可以是：

- `webhook` 侧业务代码
- workspace 内 Agent 工具调用封装
- 本地测试脚本

但不管谁调用，都必须显式给出 `dify_target_key` 与 `dataset_id`。

### 4.3 `feishu_fetch`

`feishu_fetch` 直接读取自己的根 `.env` 配置，例如：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_REQUEST_TIMEOUT_SECONDS`
- `LARK_CLI_COMMAND`
- `MARKITDOWN_COMMAND`

`feishu_fetch` 的业务参数仍由运行时显式传入，例如：

- `document_id`
- `file_token`
- `doc_type`
- `output_dir`

不把这些业务参数塞回根 `.env`。

### 4.4 `old_code/` 下旧 `.env` 的处理边界

当前仓库中若存在两份 `.env`：

- `c:\WorkPlace\NewVLA\old_code` 下的旧 `.env` 仅作历史参照，不属于当前主链路配置源
- 仓库根目录 `.env` 是当前主链路唯一有效的静态配置源

因此：

- 新主链路代码只允许读取仓库根目录 `.env`
- 不读取 `old_code/` 下旧 `.env`
- 不保留、兼容或继续扩大旧 `.env` 的依赖面

## 5. Dify 合同收口

### 5.1 运行时合同

运行时必须显式提供：

- `dify_target_key`
- `dataset_id`

其中：

- `task_context.json` 中的 `dify_target_key` 与 `dataset_id` 均为必填非空字符串
- 缺失、空字符串、或仅包含空白字符都按配置错误处理

运行时不提供：

- `api_base`
- `api_key`
- `http_verify`
- `timeout_seconds`

### 5.2 根 `.env` 合同

根 `.env` 中允许存在一组或多组按统一环境变量命名规则声明的 Dify 静态目标配置，运行时以 `dify_target_key` 命中对应配置组。

唯一命名规则如下：

- `DIFY_TARGET_<KEY>_API_BASE`
- `DIFY_TARGET_<KEY>_API_KEY`
- `DIFY_TARGET_<KEY>_HTTP_VERIFY`
- `DIFY_TARGET_<KEY>_TIMEOUT_SECONDS`

其中：

- `<KEY>` 为 `dify_target_key` 的大写环境变量形式
- 所有模块必须使用同一套命名规则解析，不允许各自定义别名或兼容写法

每个目标至少要能解析出：

- `api_base`
- `api_key`
- `http_verify`
- `timeout_seconds`

也就是说，根 `.env` 必须承担：

```text
dify_target_key
  -> api_base
  -> api_key
  -> http_verify
  -> timeout_seconds
```

但不承担：

```text
folder_token
  -> dataset_id
  -> qa_rule_file
```

这层业务映射应留在 `webhook` 路由配置，不放进根 `.env`。

根 `.env` 中不允许存在作为默认目标的：

- `DIFY_DATASET_ID`

若后续实现中检测到根 `.env` 仍包含非空 `DIFY_DATASET_ID`，应按配置错误处理并明确报错。

建议错误口径：

- `dify config error: DIFY_DATASET_ID is not allowed in root .env; dataset_id must come from runtime context`
- `dify config error: dify_target_key is missing; runtime must provide the target key explicitly`
- `dify config error: unknown dify_target_key=team_a; no matching Dify target config found in root .env`

### 5.3 调用侧合同

调用 `dify_upload` 时，最低必要输入应为：

- 运行时显式给出的 `dify_target_key`
- 运行时显式给出的 `dataset_id`
- 待上传文件路径

`dify_upload` 自己负责从根 `.env` 补齐：

- `api_base`
- `api_key`
- `http_verify`
- `timeout_seconds`

## 6. 文件与目录设计

本轮只定义跨模块配置合同与责任边界，不定义模块内部目录结构。

## 7. 模块级设计

### 7.1 `dify_upload`

`dify_upload` 只承担两件事：

- 根据运行时 `dify_target_key` 从根 `.env` 读取对应静态 Dify 配置
- 将运行时 `dify_target_key`、`dataset_id` 与静态配置合成为最终上传目标

本 spec 不约束该模块内部的类名、函数名与文件组织。

### 7.2 `feishu_fetch`

`feishu_fetch` 直接从根 `.env` 读取自身静态配置，运行时只显式接收文档标识、文件标识、输出目录等业务参数。

本 spec 不约束 `feishu_fetch` 的内部实现结构，详细实现以 `feishu_fetch` 独立 spec 为准。

### 7.3 `webhook`

`webhook` 设计保持不变，但补三条硬规则：

- `task_context.json` 中的 `dify_target_key` 是必填字段
- `task_context.json` 中的 `dataset_id` 是必填字段
- 若上游路由阶段拿不到 `dify_target_key` 或 `dataset_id`，应在进入上传环节前失败，而不是让下游模块兜底猜测

### 7.4 `folder_token` 一对一映射合同

`webhook` 路由配置必须承担以下业务映射：

```text
folder_token
  -> dify_target_key
  -> dataset_id
  -> qa_rule_file
```

含义：

- `folder_token` 决定业务线
- `dify_target_key` 决定去根 `.env` 中取哪一套 Dify 实例配置
- `dataset_id` 决定该实例中的目标知识库
- `qa_rule_file` 决定本次任务读取哪一份 QA 合同

Agent 不负责推断这三者的映射关系。

补充约束：

- `qa_rule_file` 必须是工作区 `rules/` 目录下的相对路径
- 禁止绝对路径
- 禁止包含 `..` 跳目录

## 8. 运行时数据流

```text
folder_token / document event
  -> webhook 路由
  -> 明确得到 dify_target_key + dataset_id + qa_rule_file
  -> 写入 task_context.json
  -> Agent / 调用侧显式传入 dify_target_key + dataset_id
  -> dify_upload 按 dify_target_key 从根 .env 读取静态 Dify 配置
  -> 完成上传
```

Feishu 抓取链路：

```text
task_context / tool input
  -> 显式传入 document_id / file_token / output_dir
  -> feishu_fetch 从根 .env 读取静态飞书配置
  -> 完成抓取
```

## 9. 错误与校验

### 9.1 `dify_upload`

以下情况必须 fail fast：

- 运行时未传 `dify_target_key`
- 运行时未传 `dataset_id`
- `dify_target_key` 为空字符串
- `dataset_id` 为空字符串
- 根 `.env` 中不存在与 `dify_target_key` 匹配的 Dify 目标配置
- 根 `.env` 包含非空 `DIFY_DATASET_ID`

### 9.2 `feishu_fetch`

以下情况必须 fail fast：

- 根 `.env` 缺 `FEISHU_APP_ID`
- 根 `.env` 缺 `FEISHU_APP_SECRET`
- `LARK_CLI_COMMAND` 不存在且无默认可执行命令

### 9.3 `webhook`

以下情况必须 fail fast：

- 路由后未得到 `dify_target_key`
- 路由后未得到 `dataset_id`
- 路由后未得到 `qa_rule_file`
- 生成 `task_context.json` 时遗漏 `dify_target_key`
- 生成 `task_context.json` 时遗漏 `dataset_id`

## 10. 对现有设计的覆盖关系

本设计覆盖并修正以下旧假设：

- “`dify_upload` 的完整目标配置应总由模块外适配层先组装好再传入”
- “根 `.env` 中可以保留默认 `DIFY_DATASET_ID`”
- “只有 `webhook` 直接读根 `.env`，其他模块应主要依赖外部组装”
- “`dataset_id` 单独注入就足够，不需要标明 Dify 实例”

新的口径是：

- 各模块都可直接读取根 `.env` 的本模块配置分组
- `dify_target_key` 与 `dataset_id` 只能来自运行时显式输入
- LLM 不承担静态基础设施配置注入

## 11. 成功标准

- `webhook`、`dify_upload`、`feishu_fetch` 都有清晰的根 `.env` 消费边界
- `dify_target_key` 与 Dify 实例配置的对应关系明确，不再靠实现期猜测
- `dataset_id` 的来源明确，必须来自运行时显式输入
- `folder_token -> dify_target_key + dataset_id + qa_rule_file` 的映射关系明确
- 根 `.env` 不再承担默认业务目标注入职责
- legacy Feishu 配置继续保留，但不会与主链路合同混用
- 根 `.env` 出现非空 `DIFY_DATASET_ID` 时，模块启动即报配置错误
- 运行时缺 `dify_target_key` 或 `dataset_id` 时，进入上传前即失败
- 传入未知 `dify_target_key` 时，模块报 `unknown dify target config` 错误
- 路由配置缺 `dify_target_key`、`dataset_id` 或 `qa_rule_file` 任一字段时，`webhook` 不生成有效 `task_context.json`
