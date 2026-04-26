# Feishu Fetch Lark CLI Design

## 1. 背景与目标

本设计用于重构旧的 `old_code/feishu_fetch` 参考实现，在 `c:\WorkPlace\NewVLA\feishu_fetch` 下建设新的飞书正文抓取模块。

旧代码只作参考，不直接搬运。新模块的目标不是做一个通用飞书 SDK，而是为当前仓库已经确定的自动化链路提供一个 **agent 友好**、可被 Cursor CLI 中 LLM 方便调用的正文抓取能力。

当前整体链路已经明确：

- 飞书 webhook 负责接收事件、做幂等与调度
- 执行器在目标工作区启动 Cursor CLI
- Agent 在工作区内按任务上下文处理飞书文档
- 后续还会进入 QA 抽取、CSV 生成、Dify 上传等步骤

因此 `feishu_fetch` 的职责应收敛为：

- 接收结构化抓取请求
- 调用 `lark-cli` 直接拉取飞书 docx 原文并落盘
- 下载飞书 drive 文件后，按格式决定是原文件直出，还是经 `MarkItDown` 转成正文后落盘
- 返回统一的产物结果
- 在失败时抛出对 LLM 友好的异常

## 2. 设计原则

- Agent 友好：对外只暴露单一高层入口，减少 LLM 组装多步调用的成本
- 显式优先：输入使用结构化字段，不依赖 URL 猜测，也不依赖模块内部推断
- 依赖诚实：`lark-cli` 和 `MarkItDown` 都视为第三方依赖，按路径做软检测，不自动安装
- 边界清晰：本模块只负责抓正文，不承担 webhook、路由、QA、上传等上游或下游职责
- 失败可执行：异常信息先服务 LLM 判断下一步，再补充最小必要技术细节
- 最小可用：第一版只支持当前明确需要的抓取路径和旧实现白名单内的类型

## 3. 非目标

- 不在本模块中实现飞书 webhook 事件解析
- 不在本模块中实现 `folder_token` 业务路由
- 不在本模块中实现 QA 抽取
- 不在本模块中实现 Dify 上传
- 不在本模块中自动安装或自动配置 `lark-cli`
- 不在本模块中自动登录或修复 `lark-cli` 认证状态
- 不在第一版中支持旧实现白名单之外的新文件类型
- 不在第一版中同时维护 Python OpenAPI 主实现与 `lark-cli` 双后端

## 4. 与整体架构的关系

本仓库中已经明确：

- webhook 模块负责触发、幂等、调度、工作区路由与 Cursor CLI 启动
- 任务上下文由 `.cursor_task/{run_id}/task_context.json` 注入
- Agent 在工作区内根据上下文决定是否取正文、做 QA、产出 CSV 并上传

因此 `feishu_fetch` 在整体架构中的位置应为：

```text
task_context.json
    ->
Agent 读取结构化飞书字段
    ->
feishu_fetch.fetch_feishu_content(request)
    ->
落盘产物
    ->
Agent 读取产物文件
    ->
后续 QA / CSV / 上传
```

本模块不感知：

- `folder_token`
- `qa_rule_file`
- `dataset_id`
- RQ 任务流
- Cursor CLI 启动过程

本模块只接收抓取请求，只输出落盘产物结果或异常。

## 5. 总体方案选择

经设计讨论后，采用 **方案 B2：基于 `lark-cli` 的单入口 facade 封装**。

### 5.1 为什么不选旧的纯 Python OpenAPI 主实现

- 用户明确希望复用 `lark-cli` 路线
- `lark-cli` 已提供官方维护的 Docs / Drive 能力
- 对当前场景而言，目标不是做完整飞书协议层，而是提供可被 Agent 稳定调用的正文抓取能力

### 5.2 为什么不选“直通命令封装”

如果把 `lark-cli docs +fetch`、`drive +download` 等命令直接暴露给 Agent，会带来这些问题：

- 参数分散
- 命令差异大
- 错误语义不统一
- LLM 更容易串错流程

### 5.3 为什么不选“workflow 型封装”

如果 `feishu_fetch` 直接吞下更高层任务上下文并承担更多编排逻辑，会导致：

- 模块越界
- 与 webhook / Agent 主流程边界混淆
- 后续维护成本上升

因此最终选择：

- 对外只暴露一个高层抓取入口
- 内部再决定调用 `lark-cli docs +fetch` 还是 `lark-cli drive +download`

## 6. 功能范围

第一版只支持两条抓取路径：

### 6.1 `cloud_docx`

- 输入：`document_id`
- 行为：通过 `lark-cli docs +fetch --api-version v2` 直接拉取飞书 docx 原文
- 产物：将原文按 UTF-8 文本文件落盘
- 不依赖 `MarkItDown`

### 6.2 `drive_file`

- 输入：`file_token` + `doc_type`
- 行为：
  - 通过 `lark-cli drive +download` 下载文件到本地输出目录
  - 下载完成后按文件格式分流：
    - LLM 可直接读取的格式：原文件直接保留并作为主产物
    - LLM 一般不能直接读取的格式：使用 `MarkItDown` 转成正文文本后落盘
- 产物：原文件或转换后的正文文件

### 6.3 `drive_file` 的格式分流

`drive_file` 仅支持旧实现白名单内已经明确处理过的格式策略，不在第一版中扩展。

#### 6.3.1 直接落原文件

若下载后的文件属于 LLM 可直接读取的格式，则直接保留原文件作为主产物，例如：

- 图片：`.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`、`.bmp`、`.ico`、`.tif`、`.tiff`
- 文本：`.txt`、`.log`
- Markdown：`.md`、`.markdown`
- 表格文本：`.csv`、`.tsv`
- 结构化文本：`.json`、`.jsonl`、`.xml`、`.yaml`、`.yml`
- HTML / SVG：`.html`、`.htm`、`.xhtml`、`.svg`

#### 6.3.2 转正文后落盘

若下载后的文件属于 LLM 一般不能直接稳定读取的格式，则使用 `MarkItDown` 转为正文文本后落盘，例如：

- `.doc`
- `.docx`
- `.ppt`
- `.pptx`
- `.xls`
- `.xlsx`
- `.pdf`

#### 6.3.3 不支持的情况

若下载后的文件格式不在以上两类中，第一版应明确失败，而不是做模糊兜底。

## 7. 对外接口设计

### 7.1 公共入口

建议对外只导出一个高层接口：

```python
def fetch_feishu_content(request: FeishuFetchRequest) -> FeishuFetchResult:
    ...
```

Agent 的典型使用方式应尽量简单：

```python
result = fetch_feishu_content(request)
artifact_path = result.artifact_path
```

### 7.2 输入模型

建议定义 `FeishuFetchRequest`：

- `ingest_kind: Literal["cloud_docx", "drive_file"]`
- `document_id: str | None`
- `file_token: str | None`
- `doc_type: str | None`
- `output_dir: str | Path`
- `title_hint: str | None = None`
- `timeout_seconds: float | None = None`

字段语义：

- `ingest_kind`
  - 明确指定抓取路径
  - 不依赖模块内部猜测
- `document_id`
  - 仅 `cloud_docx` 使用
- `file_token`
  - 仅 `drive_file` 使用
- `doc_type`
  - 仅 `drive_file` 使用
  - 必须在白名单范围内
- `output_dir`
  - 必填
  - 指定本次抓取产物落盘目录
  - 模块不自行猜测工作区输出目录
- `title_hint`
  - 可选
  - 辅助生成下载文件名或补充结果标题
- `timeout_seconds`
  - 可选
  - 覆盖默认命令超时

### 7.3 输入校验规则

- `cloud_docx`
  - 必须提供非空 `document_id`
- `drive_file`
  - 必须同时提供非空 `file_token` 和 `doc_type`
- 所有路径
  - 必须提供可写的 `output_dir`
- 不允许传半套字段后由模块自行猜测剩余信息
- `doc_type` 不在支持范围内时立即失败

## 8. 成功返回模型

建议定义 `FeishuFetchResult`，仅表示成功态：

- `artifact_path: str`
- `artifact_kind: str`
- `title: str | None`
- `ingest_kind: str`
- `source_id: str`
- `source_type: str`
- `detail: dict[str, Any]`

字段语义：

- `artifact_path`
  - 主产物绝对路径
  - 成功时必须存在，且文件已落盘
- `artifact_kind`
  - 主产物类型
  - 建议值：
    - `docx_raw_text`
    - `drive_original_file`
    - `drive_normalized_text`
- `title`
  - 可选标题
- `ingest_kind`
  - 实际走到的抓取路径
- `source_id`
  - 对应 `document_id` 或 `file_token`
- `source_type`
  - 对应 `docx` / `sheet` / `bitable` / `slides` 等类型
- `detail`
  - 放最少必要的排障信息，例如：
    - `backend = "lark-cli"`
    - `command_used`
    - `written_filename`
    - `downloaded_filename`
    - `normalize_converter = "markitdown"`
    - `original_file_path`
    - `normalized_text_path`
    - `source_extension`

注意：

- 失败信息不再塞进返回值
- 返回值不使用 `ok=false` 这种业务态包装
- 返回值不要求内联整段正文内容，主结果是落盘产物路径

## 9. 异常模型

失败时应直接抛出异常，而不是返回失败结果。

建议定义基础异常：

```python
class FeishuFetchError(Exception):
    code: str
    retryable: bool
    llm_message: str
    detail: dict[str, Any]
```

行为约束：

- `__str__()` 返回 `llm_message`
- `llm_message` 必须对 LLM 友好
- `detail` 只保留最少必要技术信息，不直接要求 LLM 解析整段原始 stderr

### 9.1 异常子类

建议至少包含：

- `FeishuFetchError`
- `FeishuFetchDependencyError`
- `FeishuFetchAuthError`
- `FeishuFetchRequestError`
- `FeishuFetchCommandError`
- `FeishuFetchNormalizeError`
- `FeishuFetchEmptyContentError`

### 9.2 LLM 友好文案规则

异常文案统一遵循：

```text
飞书正文抓取失败：<直接原因>。
处理建议：<下一步动作>。
```

要求：

- 一句话先说清失败原因
- 再一句话给出下一步动作
- 不输出大段堆栈
- 不把整段 JSON 或整段 stderr 直接抛给 LLM
- 不只输出状态码或退出码

### 9.3 `detail` 建议字段

异常的 `detail` 中建议保留：

- `command`
- `exit_code`
- `stderr_tail`
- `source_id`
- `doc_type`
- `ingest_kind`

### 9.4 `retryable` 规则

建议默认策略：

- 参数错误：`False`
- 依赖缺失：`False`
- 权限/认证不足：`False`
- `lark-cli` 命令超时：`True`
- 临时下载失败：`True`
- 不支持类型：`False`
- 正文转换失败：默认 `False`

## 10. 第三方依赖策略

### 10.1 `lark-cli`

`lark-cli` 是主实现依赖，但采用 **软依赖检测**，不做自动安装。

约束：

- 若环境中不存在 `lark-cli`，直接抛 `FeishuFetchDependencyError`
- 模块只负责检测与调用，不负责安装
- 模块不负责自动登录或修复认证状态

### 10.2 `MarkItDown`

`MarkItDown` 同样视为第三方依赖，也采用 **软依赖检测**。

约束：

- `cloud_docx` 路径不依赖 `MarkItDown`
- `drive_file` 只有在命中“需转换格式”时才依赖 `MarkItDown`
- 若当前下载文件命中转换路径且无法导入 `MarkItDown`，抛 `FeishuFetchDependencyError`
- 不自动安装、不自动降级到其他转换器

### 10.3 按路径检测

依赖检测必须按路径进行：

- `cloud_docx`
  - 检测 `lark-cli`
- `drive_file`
  - 先检测 `lark-cli`
  - 下载文件
  - 判断文件格式
  - 若需转换，再检测 `MarkItDown`

禁止在入口处无差别检查全部依赖。

## 11. 内部模块拆分

建议目录结构：

```text
feishu_fetch/
  __init__.py
  facade.py
  models.py
  errors.py
  dependency_probe.py
  cli_runner.py
  docx_fetcher.py
  drive_fetcher.py
  artifact_store.py
  normalizer.py
```

职责划分：

- `facade.py`
  - 对外唯一公共入口
  - 负责参数校验、按 `ingest_kind` 路由、收口成功结果
- `models.py`
  - 定义输入模型与成功结果模型
- `errors.py`
  - 定义 LLM 友好异常体系
- `dependency_probe.py`
  - 检测 `lark-cli` 与 `MarkItDown`
- `cli_runner.py`
  - 统一执行 `lark-cli` 子进程
  - 负责超时、stdout/stderr 收集、退出码判断
- `docx_fetcher.py`
  - 调用 `lark-cli docs +fetch --api-version v2`
  - 解析正文
- `drive_fetcher.py`
  - 调用 `lark-cli drive +download`
  - 下载到输出目录并返回本地路径
- `artifact_store.py`
  - 负责产物目录、产物文件命名与落盘
- `normalizer.py`
  - 在命中转换路径时使用 `MarkItDown` 将文件转成正文文本

## 12. 数据流设计

### 12.1 总入口流程

```text
fetch_feishu_content(request)
  -> 校验 request
  -> 按 ingest_kind 决定所需依赖
  -> 进行软依赖检测
  -> 分流到具体抓取器
  -> 写入主产物文件
  -> 返回 FeishuFetchResult
  -> 任一步失败则抛 LLM 友好异常
```

### 12.2 `cloud_docx` 路径

```text
request(ingest_kind=cloud_docx, document_id)
  -> facade 校验 document_id
  -> 检测 lark-cli
  -> docx_fetcher 调用 docs +fetch --api-version v2
  -> 获取原文文本
  -> artifact_store 落盘为文本文件
  -> 若原文为空则抛 FeishuFetchEmptyContentError
  -> 组装 FeishuFetchResult
```

### 12.3 `drive_file` 路径

```text
request(ingest_kind=drive_file, file_token, doc_type)
  -> facade 校验参数与 doc_type 白名单
  -> 检测 lark-cli
  -> 准备 output_dir
  -> drive_fetcher 调用 drive +download
  -> 获得本地文件路径
  -> 判断文件格式
  -> 若属于 LLM 可直接读取格式:
       直接保留原文件并返回
  -> 若属于需转换格式:
       检测 MarkItDown
       normalizer 使用 MarkItDown 转正文
       artifact_store 落盘正文文件
       若正文为空则抛 FeishuFetchEmptyContentError
  -> 若格式不支持:
       抛 FeishuFetchRequestError
  -> 组装 FeishuFetchResult
```

## 13. `lark-cli` 命令策略

### 13.1 docx 读取

第一版采用 `lark-cli docs +fetch --api-version v2`。

理由：

- 该命令是官方推荐的 docs v2 读取入口
- 可直接获取 docx 原文文本
- 比直接在模块中重新实现 OpenAPI 协议更符合当前方案 B

模块内部应固定必要参数，避免把 `lark-cli` 的复杂旗标暴露给上游。抓取后的原文必须落盘，而不是只以内联字符串返回。

### 13.2 drive 下载

第一版采用 `lark-cli drive +download`。

理由：

- 已覆盖飞书 drive 文件下载
- 可让模块把重点放在“下载后如何分类处理并落盘”，而不是重复封装飞书文件下载协议

### 13.3 命令执行边界

`cli_runner` 只负责：

- 组装子进程调用
- 设置超时
- 收集 stdout / stderr
- 返回执行结果

`cli_runner` 不负责：

- 业务路由
- 解析 docx 正文语义
- 判断文件类型是否支持
- 生成 LLM 文案

## 14. 产物落盘策略

本模块的主输出是文件产物，不是临时字符串结果。

约束：

- 所有主产物必须落在调用方显式提供的 `output_dir` 内
- 不能散落到仓库根目录
- 若当前调用发生在任务运行上下文中，调用方应把 `output_dir` 指向本次任务目录下的专用子目录
- 对 `cloud_docx`，落盘的是原文文本文件
- 对可直读的 `drive_file`，落盘的是原始文件
- 对需转换的 `drive_file`，落盘的是转换后的正文文本文件
- 若实现为了转换而产生中间文件，应与主产物分离管理

第一版不要求保留所有中间文件，但必须保证主产物路径稳定、可读、可被后续 Agent 步骤直接消费。

## 15. 错误处理策略

### 15.1 分层处理

错误按以下层次归类：

- `request`
  - 参数缺失
  - 字段冲突
  - `doc_type` 不支持
- `dependency`
  - 找不到 `lark-cli`
  - 找不到 `MarkItDown`
- `command`
  - 命令退出码非 0
  - 超时
  - stdout / stderr 不符合预期
- `normalize`
  - 文件已下载，但正文转换失败
- `content`
  - 命令成功，但原文或转换后的正文为空

### 15.2 错误归因

对 `lark-cli` stderr 应做有限归因，而不是原样丢给上游。

例如：

- 提到 `login` / `auth` / `permission denied`
  - 归为认证或权限问题
- 提到命令不存在
  - 归为依赖缺失
- 提到超时
  - 归为命令超时

要求：

- 做有限、保守的归因
- 没把握时归到通用 `FeishuFetchCommandError`
- 不做过度聪明的推断

## 16. 测试策略

第一版只做值钱的测试，不追求大而全。

### 16.1 模型与校验

覆盖：

- `cloud_docx` 缺 `document_id` 时抛对的异常
- `drive_file` 缺 `file_token` / `doc_type` 时抛对的异常
- `doc_type` 不在白名单时抛对的异常

### 16.2 依赖探测

覆盖：

- 找不到 `lark-cli` 时抛对的异常
- `MarkItDown` 不可导入时，只有命中需转换格式的 `drive_file` 路径抛对的异常
- `cloud_docx` 路径不会误要求 `MarkItDown`
- 可直读的 `drive_file` 路径不会误要求 `MarkItDown`

### 16.3 CLI 交互

覆盖：

- mock 子进程成功返回
- mock 退出码非 0
- mock 超时
- mock stdout 为空或格式异常
- 验证异常是否被翻译为 LLM 友好文案

### 16.4 正文转换

覆盖：

- 可直读格式会保留原文件并返回对应产物路径
- 需转换格式能转出正文并落盘
- 不支持格式直接失败
- 转换异常被包装为 `FeishuFetchNormalizeError`

### 16.5 集成测试边界

第一版不把真实飞书联网调用纳入常规自动化测试。

原因：

- 依赖外部账号、权限与网络
- 依赖 `lark-cli` 认证状态
- 容易导致测试脆弱

建议后续单独维护手动 smoke 清单，而不是把它混进默认测试。

## 17. 手动 Smoke 建议

后续可单独维护如下手动验证项：

- `cloud_docx` 成功抓取原文并落盘
- 可直读的 `drive_file` 成功下载原文件并落盘
- 需转换的 `drive_file` 成功转正文并落盘
- 缺 `lark-cli` 时异常文案正确
- 缺 `MarkItDown` 时仅需转换的 `drive_file` 路径失败
- 认证不足时异常归因正确

## 18. 与旧代码的关系

旧代码可复用的不是整体实现，而是这些经验：

- 支持类型要收敛
- 正文抓取入口要小而稳
- 文件转换只保留当前业务需要的格式
- 出错时要尽量给出可执行结论

旧代码不再直接沿用的点：

- 不再以 Python OpenAPI 客户端作为主实现
- 不再以 URL 解析为主要输入方式
- 不再把错误统一塞进 `RuntimeError`

## 19. 第一版落地结论

第一版 `feishu_fetch` 的最终设计结论如下：

- 使用 `lark-cli` 作为主抓取后端
- 使用单入口 facade 供 Agent 调用
- 输入采用结构化参数，不以 URL 为主
- `cloud_docx` 走 docs +fetch，直接拉原文并落盘
- `drive_file` 先走 drive +download，再按格式决定原文件直出还是 `MarkItDown` 转正文后落盘
- `lark-cli` 全局软依赖，`MarkItDown` 仅对需转换格式按路径做软依赖检测
- 成功返回结构化产物结果
- 失败直接抛出 LLM 友好异常
- 自动化测试只覆盖高价值边界

该设计足以支撑后续实现计划，不需要再为第一版引入双后端、自动安装、自动认证修复或超出当前业务边界的扩展能力。
