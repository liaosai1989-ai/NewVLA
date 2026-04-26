# Root Env And Dify Target Contract Design

## 1. 背景与目标

本设计用于同时收口两个待优化点：

- `NTH-002 webhook 补齐 Dify 目标配置合同`
- `NTH-004 根目录 .env 与各模块配置消费合同收口`

当前仓库根目录 `.env` 已按模块分组整理，但实际消费合同还不统一：

- `webhook` 已直接读取根 `.env`
- `dify_upload` 当前更偏“显式传入完整目标配置”
- `feishu_fetch` 还没有正式落地根 `.env` 读取口径
- Dify 侧 `dataset_id`、`api_base`、`api_key` 的责任边界仍容易混淆

本设计的目标不是新增中间抽象层，而是把当前仓库的最小真实口径写死：

- 根 `.env` 是各模块共享的静态配置源
- 各模块直接读取自己负责的那组根 `.env` 配置
- LLM / `task_context.json` 只承载业务运行时参数，不承载基础设施静态配置
- Dify 的 `dataset_id` 必须运行时显式传入，根 `.env` 不允许提供默认值

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

### 2.3 `dataset_id` 必须运行时显式传入

`dataset_id` 不属于静态基础设施配置，而属于本次任务的业务目标。

因此：

- `dataset_id` 必须由运行时显式传入
- 根 `.env` 禁止提供默认 `DIFY_DATASET_ID`
- 不允许靠模块内部兜底默认值决定上传目标

这是为了避免：

- 不同 `folder_token` 或不同任务误传到同一个默认数据集
- 看似“能跑”，实际目标漂移
- 调试阶段默认值进入正式链路

## 3. 非目标

- 不新增独立顶层 resolver 包
- 不引入新的配置中心
- 不让 `webhook` 代替其他模块读取全部配置
- 不让 LLM 承担密钥和静态连接参数注入
- 不在本轮处理 legacy Feishu 配置下线，只明确其边界

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

- 必须把 `dataset_id` 作为运行时显式字段写入 `task_context.json`
- 不向任务上下文注入 `api_base`、`api_key`
- 不靠根 `.env` 的默认 `DIFY_DATASET_ID` 推断目标

### 4.2 `dify_upload`

`dify_upload` 直接读取自己的根 `.env` 配置，例如：

- `DIFY_API_BASE`
- `DIFY_API_KEY`
- `DIFY_HTTP_VERIFY`
- `DIFY_TIMEOUT_SECONDS`

`dify_upload` 不应从根 `.env` 读取默认 `dataset_id`。

该模块的合同应改为：

- 静态 Dify 连接配置由模块自己从根 `.env` 读取
- `dataset_id` 必须由调用方显式传入
- 模块内部再把“运行时 `dataset_id` + 本地静态配置”合成为最终上传目标

这里的“调用方”可以是：

- `webhook` 侧业务代码
- workspace 内 Agent 工具调用封装
- 本地测试脚本

但不管谁调用，都必须显式给 `dataset_id`。

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

### 4.4 legacy Feishu 配置

legacy Feishu 配置继续保留在根 `.env`，但定位改为：

- 兼容保留
- 非当前主链路默认依赖

新主链路代码不应继续扩大对这组 legacy 配置的依赖面。

## 5. Dify 合同收口

### 5.1 运行时合同

运行时必须显式提供：

- `dataset_id`

运行时不提供：

- `api_base`
- `api_key`
- `http_verify`
- `timeout_seconds`

### 5.2 根 `.env` 合同

根 `.env` 中允许存在：

- `DIFY_API_BASE`
- `DIFY_API_KEY`
- `DIFY_HTTP_VERIFY`
- `DIFY_TIMEOUT_SECONDS`

根 `.env` 中不允许存在作为默认目标的：

- `DIFY_DATASET_ID`

若后续实现中检测到根 `.env` 仍包含非空 `DIFY_DATASET_ID`，应按配置错误处理并明确报错。

建议错误口径：

- `dify config error: DIFY_DATASET_ID is not allowed in root .env; dataset_id must come from runtime context`

### 5.3 调用侧合同

调用 `dify_upload` 时，最低必要输入应为：

- 运行时显式给出的 `dataset_id`
- 待上传文件路径

`dify_upload` 自己负责从根 `.env` 补齐：

- `api_base`
- `api_key`
- `http_verify`
- `timeout_seconds`

## 6. 文件与目录设计

本轮不新增顶层公共配置包。

建议最小落位如下：

```text
webhook/
  src/webhook_cursor_executor/
    settings.py
    ...

dify_upload/
  src/dify_upload/
    __init__.py
    config.py
    upload.py

feishu_fetch/
  src/feishu_fetch/
    __init__.py
    config.py
    models.py
    facade.py
```

说明：

- `webhook` 继续保留现有 `settings.py`
- `dify_upload/config.py` 承担根 `.env` 的 Dify 静态配置读取
- `feishu_fetch/config.py` 作为新增薄文件，承担根 `.env` 的飞书抓取静态配置读取
- 不新增单独 resolver 包

## 7. 模块级设计

### 7.1 `dify_upload`

`dify_upload/config.py` 应拆成两层语义：

- 静态环境配置
- 最终上传目标

建议形状：

- `DifyEnvSettings`
  - 只包含 `api_base`、`api_key`、`http_verify`、`timeout_seconds`
  - 从根 `.env` 读取
  - 明确拒绝 `DIFY_DATASET_ID`
- `DifyTargetConfig`
  - 仍代表“可直接发请求的最终目标”
  - 必须包含运行时传入的 `dataset_id`

建议提供一个最小辅助入口：

```python
def build_target_config(*, dataset_id: str) -> DifyTargetConfig:
    ...
```

语义：

- 由 `dify_upload` 自己从根 `.env` 读取静态配置
- 由调用方显式传入 `dataset_id`
- 返回最终 `DifyTargetConfig`

这样既保留当前模块边界，也不把静态配置查找责任甩给外部适配层。

### 7.2 `feishu_fetch`

新增一个很薄的 `config.py`：

- `FeishuFetchSettings`
  - `app_id`
  - `app_secret`
  - `request_timeout_seconds`
  - `lark_cli_command`
  - `markitdown_command`

`facade.py` 内部使用该配置。

运行时请求对象仍只承载：

- 文档标识
- 文件标识
- 输出目录
- 文档类型

不把静态凭证和命令路径要求调用方每次重复传入。

### 7.3 `webhook`

`webhook` 设计保持不变，但补两条硬规则：

- `task_context.json` 中的 `dataset_id` 是必填字段
- 若上游路由阶段拿不到 `dataset_id`，应在进入上传环节前失败，而不是让下游模块兜底猜测

## 8. 运行时数据流

```text
folder_token / document event
  -> webhook 路由
  -> 明确得到 dataset_id
  -> 写入 task_context.json
  -> Agent / 调用侧显式传入 dataset_id
  -> dify_upload 从根 .env 读取静态 Dify 配置
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

- 运行时未传 `dataset_id`
- `dataset_id` 为空字符串
- 根 `.env` 缺 `DIFY_API_BASE`
- 根 `.env` 缺 `DIFY_API_KEY`
- 根 `.env` 包含非空 `DIFY_DATASET_ID`

### 9.2 `feishu_fetch`

以下情况必须 fail fast：

- 根 `.env` 缺 `FEISHU_APP_ID`
- 根 `.env` 缺 `FEISHU_APP_SECRET`
- `LARK_CLI_COMMAND` 不存在且无默认可执行命令

### 9.3 `webhook`

以下情况必须 fail fast：

- 路由后未得到 `dataset_id`
- 生成 `task_context.json` 时遗漏 `dataset_id`

## 10. 对现有设计的覆盖关系

本设计覆盖并修正以下旧假设：

- “`dify_upload` 的完整目标配置应总由模块外适配层先组装好再传入”
- “根 `.env` 中可以保留默认 `DIFY_DATASET_ID`”
- “只有 `webhook` 直接读根 `.env`，其他模块应主要依赖外部组装”

新的口径是：

- 各模块都可直接读取根 `.env` 的本模块配置分组
- `dataset_id` 只能来自运行时显式输入
- LLM 不承担静态基础设施配置注入

## 11. 成功标准

- `webhook`、`dify_upload`、`feishu_fetch` 都有清晰的根 `.env` 消费边界
- `DIFY_API_BASE`、`DIFY_API_KEY` 的来源明确，不再靠实现期猜测
- `dataset_id` 的来源明确，必须来自运行时显式输入
- 根 `.env` 不再承担默认业务目标注入职责
- legacy Feishu 配置继续保留，但不会与主链路合同混用
