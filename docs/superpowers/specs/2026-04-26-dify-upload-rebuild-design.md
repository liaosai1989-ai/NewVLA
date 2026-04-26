# Dify Upload Rebuild Design

## 1. 背景与目标

本设计用于重构旧的 `old_code/dify_upload` 参考实现，在 `c:\WorkPlace\NewVLA\dify_upload` 下建设新的 Dify 上传模块。

旧代码只作参考，不直接搬运。新模块需要服务于当前仓库已经确定的整体链路：

- 飞书 webhook 负责接收事件、做幂等与调度
- `webhook` 模块负责按运行时配置完成业务路由
- Agent 或上游业务流程负责生成待上传文件
- `dify_upload` 只负责将显式给定的文件上传到指定 Dify 数据集

当前总链路里的职责分工要特别说明：

- `webhook` / 运行时合同侧稳定注入的是业务目标 `dataset_id`
- `api_base`、`api_key` 属于工作区或进程本地配置，不属于 `task_context.json` 注入合同
- 在调用 `dify_upload` 之前，必须由模块外的适配层把“运行时 `dataset_id` + 本地 Dify 固定配置”组装成完整上传目标
- `dify_upload` 只消费已经解析完成的上传目标，不负责再做配置查找或业务路由

本模块的核心目标：

- 提供一个边界清晰的“纯上传”能力模块
- 接收已解析完成的 Dify 上传目标，不承担业务路由职责
- 正确调用 Dify 文件上传接口
- 对 HTTP 层和 Dify 业务层失败做稳定校验
- 返回结构化上传结果，便于上游记录与排障

## 2. 设计原则

- 边界清晰：`dify_upload` 只负责上传，不负责 `folder_token` 路由
- 合同分层：运行时只注入 `dataset_id`；完整 Dify 目标由模块外适配层组装后再传入上传函数
- 最小可用：只实现当前需要的 CSV 上传能力，不为未来假想场景扩展
- YAGNI：第一版只保留一个公共上传函数，不提前冻结内部 HTTP 抽象
- 排障友好：失败类型要可区分，返回值要足够支持上游记录

## 3. 非目标

- 不在本模块实现 `folder_token -> Dify 配置` 路由
- 不在本模块读取多文件夹业务配置文件
- 不在本模块实现审计系统
- 不在本模块实现复杂重试框架
- 不在本模块实现状态机
- 不在本模块支持多种文档格式上传
- 不在本模块支持不同 `doc_form`、自定义 `process_rule` 等可变上传策略

## 4. 与整体架构的关系

当前仓库已经确定：

- `folder_token` 的业务分流在 `webhook` 侧完成
- 运行时上下文中稳定注入的是 `dataset_id`
- `api_base`、`api_key` 由工作区或进程本地配置提供
- Agent 不负责从仓库静态资料推断目标数据集

因此本模块必须遵守以下边界：

- 输入：一个已解析完成的 Dify 上传目标 + 一个 CSV 文件
- 输出：一个结构化上传结果
- 不接收 `folder_token`
- 不依赖 `task_context.json`
- 不直接感知飞书 webhook、RQ、Cursor CLI 等上游细节

当前链路的输入合同分两层：

### 4.1 运行时合同

由 `webhook` / 任务上下文提供：

- `dataset_id`

不由运行时合同提供：

- `api_base`
- `api_key`
- HTTP 参数默认值

### 4.2 上传模块直接合同

调用 `dify_upload` 前，由模块外适配层完成目标解析，最终传入：

- `api_base`
- `api_key`
- `dataset_id`
- `http_verify`
- `timeout_seconds`

这层“目标解析”职责不属于 `dify_upload`。

## 5. 总体结构

建议目录：

```text
dify_upload/
  __init__.py
  config.py
  upload.py
```

职责拆分：

- `config.py`
  - 定义 `DifyTargetConfig`
- `upload.py`
  - 定义 `UploadResult`
  - 定义上传相关异常类型
  - 实现上传主流程
- `__init__.py`
  - 只导出稳定公共接口

## 6. 数据模型

### 6.1 Dify 目标配置

建议定义 `DifyTargetConfig`：

- `api_base: str`
- `api_key: str`
- `dataset_id: str`
- `http_verify: bool = True`
- `timeout_seconds: float = 60.0`

行为约束：

- `api_base` 支持传入 `https://host` 或 `https://host/v1`
- 模型内部提供规范化后的 `api_base_v1`
- `api_key`、`dataset_id` 必须是非空字符串
- 超时时间必须大于 0
- 该模型代表“已经解析完成、可直接发请求”的上传目标，而不是运行时注入合同本身

### 6.2 上传结果

建议定义 `UploadResult`：

- `dataset_id: str`
- `document_id: str`
- `batch: str`
- `response_body: dict[str, Any]`

约束：

- `document_id` 必须是非空字符串
- `batch` 必须是非空字符串
- 原始响应体保留为 `response_body`，便于上游记录和排障

## 7. 错误模型

旧代码统一抛 `RuntimeError`，不利于上游分类处理。第一版异常体系收敛为三类：

- `DifyUploadError`
  - 所有上传相关异常的基类
- `DifyConfigError`
  - 目标配置不合法，例如 `dataset_id` 为空
  - 错误文案应直接指出缺哪个字段，以及调用方下一步应补什么
- `DifyRequestError`
  - 请求发送前或发送中失败
  - 包括：本地文件不存在、文件不可读、文件不是 CSV、网络异常、超时、HTTP 4xx/5xx
  - 错误文案应直接指出“是本地输入问题还是远端请求问题”，避免只给底层异常原文
- `DifyResponseError`
  - 响应不是合法 JSON、JSON 结构不符合预期、业务码失败、关键字段缺失
  - 错误文案应直接指出“响应哪里不符合预期”，方便上游或 LLM 选择重试、改参或停止

错误处理原则：

- 永远不把结构异常静默吞掉
- 不把“不完整成功”当作普通成功处理
- 错误信息中应包含最小必要排障信息，例如状态码、原因短语、业务码
- 错误文案必须 LLM 友好，尽量做到“看到报错就知道怎么修”
- 优先输出“问题 + 关键上下文 + 下一步动作”，不要只抛底层库原始异常

建议错误文案风格：

- 配置错误：
  - `dify config error: dataset_id is empty; caller must provide dataset_id before upload`
  - `dify config error: api_key is empty; resolve target config before calling upload`
- 请求错误：
  - `dify request error: file is not csv; only .csv is supported in v1`
  - `dify request error: upload failed with status=401 reason=Unauthorized; check api_key or api_base`
- 响应错误：
  - `dify response error: response is not valid JSON`
  - `dify response error: missing batch in response body`
  - `dify response error: api code=123 detail=process_rule is required`

## 8. 实现方式

第一版不引入公开的 HTTP 客户端抽象。

实现约束：

- `upload.py` 内部直接基于 `httpx` 发起请求
- HTTP 细节属于模块内部实现，不作为公共 API 导出
- 默认不自动跟随重定向，避免上传文件与 `Authorization` 被错误转发
- 每次调用内部自行管理短生命周期客户端，避免“谁创建谁关闭”边界不清

这样处理的原因：

- 当前只有一个上传动作，不需要先抽出公共 HTTP 层
- 避免把 `SimpleHttpClient` 这种内部细节过早冻结成外部契约
- 后续如果确实出现多个 Dify 接口，再单独抽象

## 9. 上传主流程

建议公共入口：

```python
def upload_csv_to_dify(
    target: DifyTargetConfig,
    csv_path: Path,
    *,
    upload_filename: str | None = None,
) -> UploadResult:
    ...
```

主流程：

```text
1. 校验目标配置
2. 校验文件路径存在、可读，且扩展名为 `.csv`
3. 规范化 API Base
4. 组装 Dify 上传 URL
5. 组装 Authorization 头
6. 组装精确的 multipart/form-data
7. 发起 HTTP POST
8. 校验 HTTP 状态码
9. 解析 JSON
10. 校验 Dify 业务码与错误字段
11. 提取 document_id 与 batch
12. 缺失任一关键字段则按失败处理
13. 返回 UploadResult
```

目标 URL：

```text
{api_base_v1}/datasets/{dataset_id}/document/create-by-file
```

第一版沿用旧实现的上传参数：

- `indexing_technique = "high_quality"`
- `doc_form = "text_model"`
- `process_rule = {"mode": "automatic"}`

同时把支持范围写死为当前管线已验证的最小合同：

- 只支持 CSV 上传
- 只支持当前这组固定上传参数
- 不支持按 dataset 差异切换 `doc_form`
- 如果未来出现新的 Dify 数据集形态或参数要求，应作为新需求单独立 spec

multipart 合同也必须写死：

- 文件字段名：`file`
- 文件内容：`(upload_filename or csv_path.name, csv_bytes, "text/csv")`
- 表单字段名：`data`
- `data` 的值必须是 JSON 字符串，而不是平铺表单字段

`data` 字段内容：

```json
{
  "indexing_technique": "high_quality",
  "doc_form": "text_model",
  "process_rule": {
    "mode": "automatic"
  }
}
```

原因：

- 这是旧实现已验证的最小可用参数集合
- 当前需求没有要求把这些参数开放成复杂配置项
- 第一版避免为未知场景引入额外配置复杂度

## 10. 返回体解析规则

第一版按当前已观察到的最小成功合同判断响应，不做大范围“猜结构”。

`document_id` 提取规则只保留一处有限兼容：

- 先尝试 `body["document"]["id"]`
- 若不存在，再尝试 `body["data"]["document"]["id"]`
- 取到后统一转为字符串并做 `strip()`
- 空字符串视为缺失

`batch` 提取规则固定为：

- 只读取根级 `body["batch"]`
- 若不存在、为空或转字符串后为空，直接视为失败

业务失败判断规则：

- HTTP 4xx/5xx 直接视为失败
- JSON 解析失败视为失败
- JSON 顶层不是对象视为失败
- 若 `body.code` 存在且不在 `0 / "0" / 200 / "200"` 内，视为失败
- 若 `body.error` 存在且为真值，视为失败
- 若 `document_id` 或 `batch` 缺失，视为失败

与旧代码的关键差异：

- 旧代码在缺少 `document_id` 或 `batch` 时仅记录 warning
- 新代码将其升级为明确失败，避免上游把不完整结果误当成功
- 除 `document_id` 的单个 fallback 外，不再为未知响应结构继续加猜测分支

## 11. 对外接口

建议导出以下公共符号：

- `DifyTargetConfig`
- `UploadResult`
- `upload_csv_to_dify`
- `DifyUploadError`
- `DifyConfigError`
- `DifyRequestError`
- `DifyResponseError`

不导出内部辅助函数，例如：

- 私有请求辅助函数
- 响应解析私有函数
- `document_id` 提取私有函数

## 12. 与旧代码的关系

旧代码保留以下可复用思路：

- `api_base` 自动补齐 `/v1`
- `document_id` 的有限兼容提取
- HTTP 成功但业务失败仍按失败处理

旧代码中不延续的部分：

- 单一 `RuntimeError` 异常模型
- 上传成功但关键字段缺失只记 warning
- 公开 `SimpleHttpClient` 这类内部 HTTP 抽象
- 将可结构化结果以裸 `dict` 返回

## 13. 测试策略

第一版只覆盖高价值路径：

- 配置合法化：`api_base_v1` 自动补齐逻辑正确
- 配置校验：空 `api_key`、空 `dataset_id` 能明确失败
- 文件校验：文件不存在、不可读、非 CSV 扩展名时明确失败
- 请求合同：请求必须包含 `file` 与 `data` 两个 multipart 字段，且 `data` 为 JSON 字符串
- 请求失败：网络异常、超时、HTTP 4xx/5xx 抛出 `DifyRequestError`
- 响应解析失败：非 JSON、非对象 JSON 抛出 `DifyResponseError`
- 业务失败：`body.code` 非成功或 `body.error` 为真时抛出 `DifyResponseError`
- 关键字段缺失：缺 `document_id` 或根级 `batch` 抛出 `DifyResponseError`
- 兼容路径：`document_id` 的主路径与 fallback 路径都覆盖
- 错误文案：异常消息要包含足够上下文，并能让 LLM 或上游直接判断“补字段 / 改文件 / 重试 / 停止”
- 成功路径：返回完整 `UploadResult`

不优先编写的低价值测试：

- 过度镜像实现细节的 mock 测试
- 针对简单 dataclass 字段逐项重复断言的噪音测试

## 14. 实现边界

本 spec 只定义 `dify_upload` 模块的最小可行重构方案。

后续实现应放在 `c:\WorkPlace\NewVLA\dify_upload`，并遵守以下边界：

- 旧代码只作参考，不直接搬运
- 路由逻辑留在 `webhook`
- `dataset_id` 的运行时注入合同留在上游
- `api_base`、`api_key` 的本地配置解析留在模块外适配层
- 本模块只接收已解析完成的 Dify 上传目标
- 不引入多文件夹配置读取
- 不引入复杂重试框架
- 不引入审计或状态机
- 不导出内部 HTTP 抽象
- 不以兼容未来一切场景为目标，只满足当前管线需要

## 15. 成功标准

- 当前管线可以用“运行时 `dataset_id` + 本地固定 Dify 配置”组装目标后完成上传
- 成功时得到结构化结果，而不是裸字典
- 失败时至少能区分配置错误、请求错误、响应错误
- 模块边界与 `webhook` 不重叠
- 第一版只暴露必要公共接口，不引入多余抽象
