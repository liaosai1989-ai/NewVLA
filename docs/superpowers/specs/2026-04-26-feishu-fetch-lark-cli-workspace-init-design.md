# Feishu Fetch Lark CLI Workspace Init Design

## 1. 背景与问题

当前仓库已经确定：

- 本仓库是飞书到 Dify 自动化管线的维护仓库
- 真实执行发生在由本仓库初始化出来的 Cursor 工作区中
- `feishu_fetch` 是工作区内给 Agent 使用的正文抓取模块
- `lark-cli` 是 `feishu_fetch` 当前选定的底层抓取依赖

在已有设计里，`feishu_fetch` 曾尝试把以下内容纳入自己的根 `.env` 合同：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `LARK_CLI_COMMAND`
- `FEISHU_REQUEST_TIMEOUT_SECONDS`
- `MARKITDOWN_COMMAND`

但后续审查发现，这种设计存在三个结构性问题：

1. `feishu_fetch` 虽然读取了 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`，但真实执行链路并没有把这两个值转成 `lark-cli` 已证实会消费的配置状态，形成“读了但没真正控制运行时”的假闭环。
2. `lark-cli` 命令注入只改了一部分路径，容易出现 `cloud_docx` 生效、`drive export/poll` 回退到硬编码的隐蔽回归。
3. `MARKITDOWN_COMMAND` 被写入长期合同，但当前真实实现并不消费这个配置，属于伪配置项。

同时，本地验证与官方资料表明：

- 飞书平台能力上，应用凭证 `App ID + App Secret` 可以换取 `tenant_access_token`，并以应用身份读取文档。
- 当前安装的 `lark-cli` 支持 bot 身份访问文档，但前提是先完成 CLI 配置，而不是在调用正文抓取命令时临时塞一对环境变量就自动生效。
- 当前版本 `lark-cli` 已提供可非交互调用的 `config init`，可以把应用凭证写入当前执行环境中的 CLI 配置。

因此，本设计不再把飞书凭证配置问题塞给 `feishu_fetch` 模块内部解决，而是把它正式收口到“执行环境初始化层”。

## 2. 目标

本设计只解决一个问题：

- 在保持 `feishu_fetch` 抓取职责单一的前提下，明确 `lark-cli` 配置初始化、模块调用、错误处理和测试边界。

本设计完成后，应达到以下结果：

- `feishu_fetch` 不再直接消费 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`
- 飞书凭证进入执行环境初始化合同，而不是模块运行时合同
- `feishu_fetch` 只消费“已初始化好的 `lark-cli` 执行环境”
- `LARK_CLI_COMMAND` 在所有抓取分支统一生效，不再半接线
- `MARKITDOWN_COMMAND` 从长期合同中删除
- Agent 和模块的错误提示都能明确指出问题发生在“CLI 未初始化”、“CLI 不可执行”还是“应用权限不足”

## 3. 非目标

本设计不处理以下内容：

- 不重写 `feishu_fetch` 的正文抓取矩阵
- 不把 `lark-cli` 替换为 Python OpenAPI 主实现
- 不在 `feishu_fetch` 中自动执行交互式登录
- 不引入 user OAuth 作为第一版必需路径
- 不把飞书凭证写入 `task_context.json`
- 不让 `webhook` 在每次 `run_id` 启动时临时现配一套 CLI 认证
- 不修改旧 spec 正文；本次以新 spec 形式补充设计

## 4. 设计原则

- 边界清晰：飞书凭证属于执行环境静态基础设施配置，不属于 `feishu_fetch` 运行时业务参数
- 机器可控：抓取是否可执行，应由执行环境初始化状态决定，而不是依赖终端残留环境
- 显式优先：`task_context.json` 只承载任务级业务字段，不承载基础设施秘钥
- 够用优先：第一版只支持 bot-only 身份，不扩展到 user OAuth
- 单应用优先：第一版只支持根 `.env` 中一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 对应的同一飞书应用 bot 身份，不支持按 route 或任务切换不同应用
- 依赖诚实：按 `lark-cli` 当前已验证能力设计，不假设未证实的 env 凭证注入能力
- 失败可执行：所有错误都要输出“原因 + 处理建议”

## 5. 总体方案

采用方案：

- **执行环境初始化层负责一次性完成 `lark-cli` 配置初始化**
- **`feishu_fetch` 只消费已初始化好的 `lark-cli` 执行环境**

一句话描述：

```text
飞书凭证配置前移到执行环境初始化阶段，
正文抓取阶段只检查并使用当前执行环境里的 lark-cli 状态。
```

## 6. 模块边界

### 6.1 执行环境初始化层

第一版中，执行环境初始化层的 owner 明确为 `onboard`。

`onboard` 负责：

- 安装或接入 `lark-cli`
- 读取根 `.env` 中的飞书静态凭证
- 执行 `lark-cli config init`
- 把当前执行环境中的 `lark-cli` 配置成“bot-only 可抓取”的稳定状态

执行环境初始化层不负责：

- 具体文档抓取请求
- `document_id`、`file_token`、`doc_type` 等任务参数
- QA 抽取
- Dify 上传

### 6.2 `feishu_fetch`

`feishu_fetch` 只负责：

- 接收结构化抓取请求
- 检查 `lark-cli` 是否可执行
- 检查当前执行环境中的 `lark-cli` 是否已完成初始化
- 调用 `lark-cli` 走正文抓取链路
- 将主产物落盘并返回统一结果

`feishu_fetch` 不再负责：

- 首次配置 `lark-cli`
- 保存或解析飞书 `App ID / App Secret`
- 生成 `tenant_access_token`
- 交互式登录
- 推断当前请求应切换到哪个飞书应用
- 接管 `onboard` 负责的执行环境初始化职责

### 6.3 `webhook`

`webhook` 继续负责：

- 路由
- 调度
- `task_context.json` 写入
- `run_id` 隔离

`webhook` 不负责：

- 每次任务启动前重新配置 `lark-cli`
- 给 `feishu_fetch` 注入飞书凭证
- 首次初始化当前执行环境中的 `lark-cli`

### 6.4 `task_context.json`

`task_context.json` 仍只承载任务级业务字段，例如：

- `run_id`
- `document_id`
- `file_token`
- `doc_type`
- `dataset_id`
- `qa_rule_file`
- `dify_target_key`

明确禁止写入：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `tenant_access_token`
- 任何 `lark-cli` 内部持久化状态

## 7. 配置合同

### 7.1 执行环境初始化合同

第一版中，本合同由 `onboard` 负责落地执行。

飞书应用静态配置进入执行环境初始化合同。

初始化层从根 `.env` 读取：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

然后执行以下动作：

1. 调 `lark-cli config init --app-id <id> --app-secret-stdin`
2. 通过标准输入传入 `FEISHU_APP_SECRET`

约束：

- `config init` 必须是非交互可自动执行的形态
- 第一版不把 `config bind` 作为 Cursor 执行环境初始化的必选步骤
- 根 `.env` 只允许当前执行环境绑定一组飞书应用凭证，不支持按 `folder_token`、route 或单次任务切换不同飞书应用
- 所有进入该抓取链路的目标文档，必须事先对这同一个飞书应用 bot 身份可访问；否则应按“应用权限不足”处理，而不是在运行时切换应用兜底
- 初始化失败时，当前执行环境不得宣称自己“可执行飞书抓取”

### 7.2 `feishu_fetch` 模块合同

`feishu_fetch` 只保留真实会被模块消费的静态配置：

- `LARK_CLI_COMMAND`
- `FEISHU_REQUEST_TIMEOUT_SECONDS`

从 `feishu_fetch` 模块合同中移除：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `MARKITDOWN_COMMAND`

解释：

- `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 不再是 `feishu_fetch` 模块运行时输入
- `MARKITDOWN_COMMAND` 当前真实实现未消费，继续保留只会制造伪配置项

### 7.3 文档合同

README、spec、测试和对外示例必须统一口径：

- 飞书凭证属于执行环境初始化合同
- `feishu_fetch` 不直接读取或传递飞书凭证
- `feishu_fetch` 只要求当前执行环境中的 `lark-cli` 已完成初始化
- 命中需转换格式时，新代码固定使用 `MarkItDown` 转 Markdown
- `MarkItDown` 是实现依赖，不再通过 `MARKITDOWN_COMMAND` 暴露为配置项

## 8. 执行流

### 8.1 执行环境初始化阶段

执行环境初始化阶段流程如下：

```text
根 .env
  -> 读取 FEISHU_APP_ID / FEISHU_APP_SECRET
  -> 执行 lark-cli config init
  -> 产出可供 Agent 使用的 lark-cli 执行环境
```

此阶段完成后，当前执行环境进入“可抓取”状态。

### 8.2 任务运行阶段

单次任务运行时流程如下：

```text
task_context.json
  -> Agent 读取业务参数
  -> 调用 feishu_fetch
  -> feishu_fetch 检查 lark-cli 可执行与已初始化状态
  -> 调用 lark-cli 抓取正文
  -> 落盘到 .cursor_task/{run_id}/outputs/feishu_fetch/
```

此阶段不再发生：

- 临时注入飞书秘钥
- 临时切换应用配置
- 临时执行 `config init`

## 9. `feishu_fetch` 内部约束

### 9.1 命令入口统一

`lark-cli` 命令名必须统一从一个配置入口解析：

- `settings.lark_cli_command`

所有抓取分支都必须使用这一值，包括：

- `docs +fetch`
- `drive +download`
- `drive +export`
- `drive +task_result`
- `drive +export-download`
- 健康检查或配置检查命令

禁止在任意分支继续硬编码：

- `"lark-cli"`

### 9.2 配置检查顺序

`feishu_fetch` 执行前应按如下顺序检查：

1. `LARK_CLI_COMMAND` 可执行
2. 当前执行环境中的 `lark-cli` 已完成初始化
3. 若通过，再进入正文抓取

第一版检查入口写死为：

- `lark-cli config show`

第一版不使用：

- `lark-cli doctor --offline`

原因：

- `config show` 能直接返回当前执行环境中的 CLI 配置状态
- `doctor --offline` 会混入 user login 相关检查结果，不适合作为 bot-only 初始化完成的主判据

第一版只读取以下核心字段：

- `appId`

可辅助读取但不作为通过门槛的字段：

- `brand`
- `workspace`
- `profile`

明确不作为第一版通过门槛的字段：

- `users`
- 任何 user login 相关状态

通过标准：

1. `config show` 退出码为 `0`
2. 输出可解析出配置 JSON
3. JSON 中存在非空 `appId`
4. `appId` 与根 `.env` 中的 `FEISHU_APP_ID` 完全一致

失败标准：

- `config show` 退出码非 `0`
- 输出无法解析出配置 JSON
- JSON 中不存在 `appId`
- `appId` 为空
- `appId` 与根 `.env` 中的 `FEISHU_APP_ID` 不一致

### 9.3 不做凭证 env 注入

`feishu_fetch` 不应通过 `subprocess.run(..., env=...)` 给 `lark-cli` 临时注入：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

原因：

- 这不是当前已验证的 `lark-cli` 正式配置消费路径
- 继续这样设计会把“执行环境初始化问题”伪装成“模块运行参数问题”

## 10. 错误处理

### 10.1 CLI 不可执行

场景：

- `LARK_CLI_COMMAND` 找不到
- 命令无法启动

建议错误口径：

- 原因：找不到配置的 `lark-cli` 命令
- 处理建议：检查执行环境初始化是否已安装 CLI，或核对 `LARK_CLI_COMMAND`

### 10.2 执行环境未初始化

场景：

- `lark-cli` 可执行
- 但 `config show` 无法返回有效的当前应用配置

具体包括：

- `config show` 执行失败
- `config show` 输出无法解析
- `config show` 返回中缺少非空 `appId`
- `config show` 返回的 `appId` 与根 `.env` 中的 `FEISHU_APP_ID` 不一致

建议错误口径：

- 原因：当前执行环境未完成 `lark-cli` 初始化，或当前配置的应用与根 `.env` 不一致
- 处理建议：回到执行环境初始化流程，重新执行 `config init` 后重试

### 10.3 应用权限不足

场景：

- `lark-cli` 已初始化
- 但 bot 身份对目标文档无访问权限

建议错误口径：

- 原因：当前应用身份对目标文档无权限，或缺少对应 scope
- 处理建议：在飞书开放平台补应用权限，或为应用授予目标文档访问权限后重试

第一版验收要求：

- 必须通过真实抓取命令验证该类错误，而不是仅通过环境检查命令推断
- 第一版最小必测路径固定为 `cloud_docx` 对应的真实抓取命令
- 在“目标文档已授权给当前应用”场景下，真实抓取命令必须成功并产出正文
- 在“目标文档未授权给当前应用”场景下，真实抓取命令必须失败，且错误必须归类为“应用权限不足”
- 该失败不得被误判为“执行环境未初始化”或“CLI 不可执行”
- 该失败过程中，不得尝试切换飞书应用身份、读取第二组飞书凭证或触发 user login 兜底

### 10.4 命令参数与当前版本漂移

场景：

- 仓库代码使用的 `lark-cli` 参数，与当前已安装版本 help 不一致

建议处理：

- 以当前已验证版本的 `lark-cli` help 和实测行为为准，修正规格与实现
- 不再继续依赖过期命令形态

### 10.5 伪配置项

场景：

- 文档、测试或 dataclass 仍宣称 `MARKITDOWN_COMMAND` 可控制转换逻辑

建议处理：

- 直接从合同、`.env` 示例、settings/dataclass 和配置相关测试中删除该配置
- 保留“新代码命中需转换格式时固定使用 `MarkItDown`”这一实现口径
- 不新增“未来可能会用”的预留配置项

## 11. 测试设计

### 11.1 应删除的测试方向

不再保留以下测试方向：

- `feishu_fetch` 从根 `.env` 读取 `FEISHU_APP_ID`
- `feishu_fetch` 从根 `.env` 读取 `FEISHU_APP_SECRET`
- `MARKITDOWN_COMMAND` dataclass 形状稳定性

这些测试对应的合同已经不成立。

### 11.2 应新增或保留的测试方向

应覆盖以下行为：

- 所有抓取分支都统一使用 `settings.lark_cli_command`
- `drive export` 轮询路径不回退到硬编码 `"lark-cli"`
- 执行环境未初始化时，抛出 LLM 友好错误
- `config show` 返回的 `appId` 与根 `.env` 中的 `FEISHU_APP_ID` 不一致时，按初始化失败处理
- `LARK_CLI_COMMAND` 不可执行时，抛出 LLM 友好错误
- 对已授权给当前应用的 `cloud_docx`，真实抓取命令成功并产出正文
- 对未授权给当前应用的 `cloud_docx`，真实抓取命令失败并明确归类为“应用权限不足”
- 权限失败场景下，不尝试切换飞书应用身份、不读取第二组飞书凭证、不触发 user login 兜底
- `FEISHU_REQUEST_TIMEOUT_SECONDS` 仍按正数配置校验

### 11.3 回归重点

本轮最关键的回归点有三个：

1. `cloud_docx`
2. `drive_file export + poll`
3. `MARKITDOWN_COMMAND` 从合同与配置形状中彻底删除，同时转换路径仍固定使用 `MarkItDown`

其中 `cloud_docx` 回归必须同时覆盖：

- 当前应用有权限时抓取成功
- 当前应用无权限时稳定报“应用权限不足”

## 12. 对其他设计文档的影响

本 spec 是增量补充，不直接改写旧 spec 正文。

但后续在实现与计划阶段，应同步修正以下认知：

- 旧文档里若把 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 写成 `feishu_fetch` 模块合同，应视为已被本 spec 覆盖
- 旧文档里若保留 `MARKITDOWN_COMMAND`，应视为已被本 spec 否定
- 旧文档里若把“删除 `MARKITDOWN_COMMAND`”误写成“不再使用 `MarkItDown`”，应以本 spec 当前正文为准修正
- 旧文档里若默认 `feishu_fetch` 自己接管 CLI 凭证，应以本 spec 为准

## 13. 成功标准

以下条件同时满足，才算该设计落地正确：

- 执行环境初始化层能一次性把 `lark-cli` 配置成 bot-only 可用状态
- 所有进入该抓取链路的文档，都能被根 `.env` 中这同一个飞书应用 bot 身份访问
- `feishu_fetch` 不再读取或保存飞书凭证
- `feishu_fetch` 的所有 `lark-cli` 分支都走统一命令入口
- 命中需转换格式时，新代码固定使用 `MarkItDown`，且不通过 `MARKITDOWN_COMMAND` 暴露配置项
- 未初始化执行环境、命令缺失、应用权限不足三类错误都能被明确区分
- 对未授权给当前应用的目标文档，真实抓取命令会稳定失败并归类为“应用权限不足”，且不会触发切换应用或其他运行时兜底

## 14. 开放问题与后续阶段

本设计确认后，下一阶段应进入实现计划，明确：

- `onboard` 中执行环境初始化代码的具体文件组织与调用入口
- `config init` 的自动化执行细节
- `feishu_fetch` 中配置检查函数的具体实现
- 旧测试、README 和 plan 的迁移步骤

本设计不继续展开实现顺序，交由后续 implementation plan 收敛。
