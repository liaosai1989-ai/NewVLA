# Feishu Fetch Lark CLI Design

## 修订说明（2026-04-26 单应用 bot 抓取前提补充）

本文件以下正文保留原文，不直接改写原设计内容。

针对后续确认的 `lark-cli` 工作区初始化口径，现补充以下修订说明；若与正文旧表述冲突，以本修订说明为准：

- 第一版 `feishu_fetch` 抓取链路默认建立在“单工作区 + 单飞书应用 bot 身份”前提上
- 仓库根 `.env` 中飞书侧只允许一组 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 作为当前工作区初始化来源，不支持按 route 或单次任务切换不同飞书应用
- 所有进入该抓取链路的目标文档，必须事先对这同一个飞书应用 bot 身份可访问
- 若目标文档对该应用不可访问，应按“应用权限不足”处理，而不是在 `feishu_fetch` 运行时切换应用身份兜底
- `feishu_fetch` 不负责推断当前请求应绑定哪个飞书应用；相关初始化边界以 [2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](file:///c:/WorkPlace/NewVLA/docs/superpowers/specs/2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md) 为准

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
- 下载飞书 drive 文件后，按第一版固定支持矩阵决定是原文件直出，还是经 `MarkItDown` 转成 Markdown 后落盘
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

### 4.1 上游注入闭环

为了避免 Agent 在运行时猜参数，第一版要求上游在 `task_context.json` 中显式注入 `feishu_fetch` 所需字段。

推荐方式：

- 直接注入一个 `feishu_fetch_request`
- 或至少注入以下等价字段：
  - `ingest_kind`
  - `document_id`
  - `file_token`
  - `doc_type`

约束：

- `drive_file` 不能只给 `document_id`，必须显式给 `file_token` 和 `doc_type`
- Agent 不允许根据 `event_type`、URL、仓库文档或历史经验自行猜测 `doc_type`
- 自动化运行场景下，`output_dir` 应显式指向 `.cursor_task/{run_id}/outputs/feishu_fetch/`
- 本模块只消费显式传入的抓取参数，不负责从 webhook 事件体重新推导抓取请求

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
- 内部再决定调用 `lark-cli docs +fetch`、`lark-cli drive +download` 或 `lark-cli drive +export`

## 6. 功能范围

第一版只支持两条抓取路径：

### 6.1 `cloud_docx`

- 输入：`document_id`
- 行为：通过 `lark-cli docs +fetch --api-version v2 --format json --doc-format xml --detail simple` 获取文档导出内容
- 提取：从返回的 JSON envelope 中读取 `data.document.content`
- 产物：将导出内容按 UTF-8 文本文件落盘
- 不依赖 `MarkItDown`

### 6.2 `drive_file`

- 输入：`file_token` + `doc_type`
- 行为：
  - 先按飞书对象类型分流命令路径
  - 再按落盘后的本地文件格式决定是原文件直出，还是交给 `MarkItDown`
- 产物：原文件或转换后的 Markdown 文件

### 6.3 `drive_file` 的命令分流

`drive_file` 不能统一建模成“先 `drive +download` 再按扩展名处理”。

第一版按 `doc_type` 分流如下：

#### 6.3.1 `file`

- 走 `lark-cli drive +download`
- 下载后再按本地扩展名判断是否原文件直出

#### 6.3.2 `doc` / `docx` / `sheet`

- 优先走 `lark-cli drive +export`
- 导出目标格式必须显式固定，不允许依赖 CLI 默认值
- 若导出轮询窗口内未完成：
  - 继续走有上限的 `lark-cli drive +task_result --scenario export`
  - 拿到导出文件 token 后，再走 `lark-cli drive +export-download`
- 若在总超时预算内仍拿不到导出结果，则直接失败，不做无限轮询

第一版固定导出合同如下：

| `doc_type` | 命令链 | 固定导出格式 | 预期本地扩展名 | 后续处理 |
| --- | --- | --- | --- | --- |
| `doc` | `drive +export` -> bounded `task_result` -> `export-download` | `docx` | `.docx` | 交给 `MarkItDown` |
| `docx` | `drive +export` -> bounded `task_result` -> `export-download` | `docx` | `.docx` | 交给 `MarkItDown` |
| `sheet` | `drive +export` -> bounded `task_result` -> `export-download` | `xlsx` | `.xlsx` | 交给 `MarkItDown` |

说明：

- 实现时必须显式传入对应的导出格式参数
- 若 `lark-cli` 实测不支持上述固定导出格式，则对应类型应从第一版支持范围移除，而不是在实现时临时改合同

#### 6.3.3 `slides` / `mindnote`

- 当前只有对象类型层面的间接信息
- 还没有足够证据证明其第一版命令链应走 `download`、`export` 或专属域命令
- 因此第一版不纳入支持范围

#### 6.3.4 `bitable`

- `bitable` 虽然在 `drive +export` 语义上有间接信息，但当前没有被第一版正文链路验证为稳定、可消费的固定输出
- 为避免把不稳定导出格式写进 v1 合同，第一版移出支持范围
- 后续若补齐独立验证，再以单独 spec 修订加入

### 6.4 `drive_file` 的格式分流

`drive_file` 仅支持旧实现白名单内、且命令链已验证清楚的格式策略，不在第一版中扩展。

#### 6.4.1 直接落原文件

若下载后的文件属于 LLM 可直接读取的格式，则直接保留原文件作为主产物，例如：

- 图片：`.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`、`.bmp`、`.ico`、`.tif`、`.tiff`
- 文本：`.txt`、`.log`
- Markdown：`.md`、`.markdown`
- 表格文本：`.csv`、`.tsv`
- 结构化文本：`.json`、`.jsonl`、`.xml`、`.yaml`、`.yml`
- HTML / SVG：`.html`、`.htm`、`.xhtml`、`.svg`

#### 6.4.2 转 Markdown 后落盘

若下载或导出后的文件属于 LLM 一般不能直接稳定读取的格式，则使用 `MarkItDown` 转为 Markdown 文本后落盘，例如：

- `.doc`
- `.docx`
- `.ppt`
- `.pptx`
- `.xls`
- `.xlsx`
- `.pdf`

#### 6.4.3 不支持的情况

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
  - 第一版白名单仅包含 `file`、`doc`、`docx`、`sheet`
- `output_dir`
  - 必填
  - 指定本次抓取产物落盘目录
  - 模块不自行猜测工作区输出目录
  - 自动化运行场景下，推荐显式传入 `.cursor_task/{run_id}/outputs/feishu_fetch/`
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
- 不允许把 `document_id` 当作 `drive_file` 的兜底输入

## 8. 成功返回模型

建议定义 `FeishuFetchResult`，仅表示成功态：

- `artifact_path: str`
- `ingest_kind: str`
- `title: str | None`

字段语义：

- `artifact_path`
  - 主产物绝对路径
  - 成功时必须存在，且文件已落盘
- `ingest_kind`
  - 实际走到的抓取路径
- `title`
  - 可选标题
  - 仅用于帮助 Agent 理解产物来源，不承担排障语义

注意：

- 失败信息不再塞进返回值
- 返回值不使用 `ok=false` 这种业务态包装
- 返回值不要求内联整段正文内容，主结果是落盘产物路径
- 排障细节不固化进成功返回合同，需要时由日志或调用侧调试信息承接

## 9. 异常模型

失败时应直接抛出异常，而不是返回失败结果。

建议定义基础异常：

```python
class FeishuFetchError(Exception):
    code: str
    llm_message: str
    detail: dict[str, Any]
```

行为约束：

- `__str__()` 返回 `llm_message`
- `llm_message` 必须对 LLM 友好
- `detail` 只保留最少必要技术信息，不直接要求 LLM 解析整段原始 stderr

### 9.1 错误码

第一版不再维护过细的异常子类树，只保留一个基础异常类，并用稳定 `code` 区分错误类型。

建议错误码：

- `request_error`
- `dependency_error`
- `runtime_error`
- `empty_content`

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
- `ingest_kind`
- `doc_type`

### 9.4 错误归类原则

第一版只做保守归类：

- 参数缺失、字段冲突、`doc_type` 不支持
  - `request_error`
- `lark-cli` 或 `MarkItDown` 不可用
  - `dependency_error`
- `lark-cli` 执行失败、导出超时、认证失败、下载失败、转换失败
  - `runtime_error`
- 成功拿到结果但正文为空
  - `empty_content`

说明：

- 是否重试不是本模块合同的一部分
- 调度层若需要重试，应基于 `code` 和运行上下文自行决策

## 10. 第三方依赖策略

### 10.1 `lark-cli`

`lark-cli` 是主实现依赖，但采用 **软依赖检测**，不做自动安装。

约束：

- 若环境中不存在 `lark-cli`，直接抛 `dependency_error`
- 依赖检测不只看命令名是否存在，还要确认命令可以被实际启动
- 模块只负责检测与调用，不负责安装
- 模块不负责自动登录或修复认证状态

### 10.2 `MarkItDown`

`MarkItDown` 同样视为第三方依赖，也采用 **软依赖检测**。

约束：

- `cloud_docx` 路径不依赖 `MarkItDown`
- `drive_file` 只有在命中“需转换格式”时才依赖 `MarkItDown`
- 若当前下载文件命中转换路径且无法导入 `MarkItDown`，抛 `dependency_error`
- 不自动安装、不自动降级到其他转换器
- `MarkItDown` 的目标产物是 Markdown，不应在合同中泛化成 plain text

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
```

职责划分：

- `facade.py`
  - 对外唯一公共入口
  - 负责参数校验、按 `ingest_kind` 路由、依赖检测、命令调用、落盘和收口成功结果
  - 第一版将 `cloud_docx` / `drive_file` 的流程以内聚私有函数实现，不为未来扩展提前拆文件
- `models.py`
  - 定义输入模型与成功结果模型
- `errors.py`
  - 定义 LLM 友好异常体系

说明：

- 只有当第二后端、第二转换器或明显复用出现后，才考虑再拆子进程执行器、正文转换器等独立模块
- 第一版优先保证文件少、流程清楚、调用边界稳定

## 12. 数据流设计

### 12.1 总入口流程

```text
fetch_feishu_content(request)
  -> 校验 request
  -> 先检测 lark-cli 是否可实际启动
  -> 分流到具体抓取器
  -> 写入主产物文件
  -> 返回 FeishuFetchResult
  -> 任一步失败则抛 LLM 友好异常
```

### 12.2 `cloud_docx` 路径

```text
request(ingest_kind=cloud_docx, document_id)
  -> facade 校验 document_id
  -> 检测 lark-cli 可实际启动
  -> facade 私有函数调用 docs +fetch --api-version v2 --format json --doc-format xml --detail simple
  -> 从 JSON envelope 提取 data.document.content
  -> facade 私有函数落盘为文本文件
  -> 若 content 为空则抛 `empty_content`
  -> 组装 FeishuFetchResult
```

### 12.3 `drive_file` 路径

```text
request(ingest_kind=drive_file, file_token, doc_type)
  -> facade 校验参数与 doc_type 白名单
  -> 检测 lark-cli 可实际启动
  -> 准备 output_dir
  -> 若 doc_type == file:
       facade 私有函数调用 drive +download
  -> 若 doc_type in {doc, docx, sheet}:
       按固定导出矩阵显式传参调用 drive +export
       若导出未完成:
         在总超时预算内有上限地轮询 drive +task_result --scenario export
         成功后调用 drive +export-download
       若超过总超时预算:
         抛 runtime_error
  -> 若 doc_type in {bitable, slides, mindnote}:
       抛 request_error
  -> 获得本地文件路径
  -> 判断文件格式
  -> 若属于 LLM 可直接读取格式:
       直接保留原文件并返回
  -> 若属于需转换格式:
       再检测 MarkItDown
       facade 私有函数使用 MarkItDown 转 Markdown
       facade 私有函数落盘 Markdown 文件
       若 Markdown 为空则抛 empty_content
  -> 若格式不支持:
       抛 request_error
  -> 组装 FeishuFetchResult
```

## 13. `lark-cli` 命令策略

### 13.1 docx 读取

第一版采用 `lark-cli docs +fetch --api-version v2`。

理由：

- 该命令是官方推荐的 docs v2 读取入口
- 默认返回 JSON envelope，可从 `data.document.content` 取出文档导出内容
- 比直接在模块中重新实现 OpenAPI 协议更符合当前方案 B

模块内部应固定必要参数，避免把 `lark-cli` 的复杂旗标暴露给上游。第一版建议固定：

- `--format json`
- `--doc-format xml`
- `--detail simple`
- `--scope` 也应显式固定，不能依赖 CLI 默认值

抓取后的内容必须落盘，而不是只以内联字符串返回。

### 13.2 drive 导出与下载

第一版不再统一采用 `lark-cli drive +download`。

理由：

- `file` 类型适合 `drive +download`
- 第一版只保留能写死导出结果的 `doc` / `docx` / `sheet`
- `doc` / `docx` 固定导出为 `.docx`
- `sheet` 固定导出为 `.xlsx`
- `bitable`、`slides`、`mindnote` 因固定输出未验证，不纳入第一版
- `drive +export` 超时后只做有上限的补充轮询，不做无限等待

第一版导出链的实现约束：

- 显式传入导出格式参数
- 维护一个总超时预算
- `task_result` 轮询必须有固定间隔和最大次数
- 超出预算后直接抛 `runtime_error`

### 13.3 命令执行边界

内部子进程执行辅助逻辑只负责：

- 组装子进程调用
- 设置超时
- 收集 stdout / stderr
- 返回执行结果

内部子进程执行辅助逻辑不负责：

- 业务路由
- 解析 docx 正文语义
- 判断文件类型是否支持
- 生成 LLM 文案

## 14. 产物落盘策略

本模块的主输出是文件产物，不是临时字符串结果。

约束：

- 所有主产物必须落在调用方显式提供的 `output_dir` 内
- 不能散落到仓库根目录
- 若当前调用发生在任务运行上下文中，调用方应把 `output_dir` 指向 `.cursor_task/{run_id}/outputs/feishu_fetch/`
- 对 `cloud_docx`，落盘的是原文文本文件
- 对可直读的 `drive_file`，落盘的是原始文件
- 对需转换的 `drive_file`，落盘的是转换后的 Markdown 文件
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
  - `lark-cli` 不存在或不可实际启动
  - 找不到 `MarkItDown`
- `command`
  - 命令退出码非 0
  - 超时
  - stdout / stderr 不符合预期
- `normalize`
  - 文件已下载或导出，但 Markdown 转换失败
- `content`
  - 命令成功，但导出内容或转换后的 Markdown 为空

### 15.2 错误归因

对 `lark-cli` stderr 应做有限归因，而不是原样丢给上游。

例如：

- 提到 `login` / `auth` / `permission denied`
  - 归入 `runtime_error`
- 提到命令不存在或命令无法启动
  - 归入 `dependency_error`
- 提到超时
  - 归入 `runtime_error`

要求：

- 做有限、保守的归因
- 没把握时归到通用 `runtime_error`
- 不做过度聪明的推断

## 16. 测试策略

第一版只做值钱的测试，不追求大而全。

### 16.1 模型与校验

覆盖：

- `cloud_docx` 缺 `document_id` 时抛对的异常
- `drive_file` 缺 `file_token` / `doc_type` 时抛对的异常
- `doc_type` 不在白名单时抛对的异常
- `drive_file` 只给 `document_id` 时抛对的异常

### 16.2 依赖探测

覆盖：

- 找不到 `lark-cli` 时抛对的异常
- `MarkItDown` 不可导入时，只有命中需转换格式的 `drive_file` 路径抛对的异常
- `cloud_docx` 路径不会误要求 `MarkItDown`
- 可直读的 `drive_file` 路径不会误要求 `MarkItDown`
- `lark-cli` 名称存在但无法实际启动时抛对的异常

### 16.3 CLI 交互

覆盖：

- mock 子进程成功返回
- mock 退出码非 0
- mock 超时
- mock stdout 为空或格式异常
- 验证异常是否被翻译为 LLM 友好文案
- 验证 `doc/docx/sheet` 是否显式带上固定导出格式参数

### 16.4 正文转换

覆盖：

- 可直读格式会保留原文件并返回对应产物路径
- 需转换格式能转出 Markdown 并落盘
- 不支持格式直接失败
- 转换异常被包装为 `runtime_error`

### 16.5 集成测试边界

第一版不把真实飞书联网调用纳入常规自动化测试。

原因：

- 依赖外部账号、权限与网络
- 依赖 `lark-cli` 认证状态
- 容易导致测试脆弱

建议后续单独维护手动 smoke 清单，而不是把它混进默认测试。

## 17. 手动 Smoke 建议

后续可单独维护如下手动验证项：

- `cloud_docx` 成功从 `data.document.content` 提取导出内容并落盘
- 可直读的 `drive_file` 成功下载原文件并落盘
- 需转换的 `drive_file` 在 `doc/docx/sheet` 固定导出矩阵下成功转 Markdown 并落盘
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
- 上游必须显式注入 `feishu_fetch_request` 或等价字段，不允许 Agent 猜 `drive_file` 参数
- `cloud_docx` 走 docs +fetch，从 `data.document.content` 提取导出内容并落盘
- `drive_file` 按 `doc_type` 分命令链：`file` 走 download；`doc/docx` 固定导出为 `.docx`；`sheet` 固定导出为 `.xlsx`
- `bitable`、`slides`、`mindnote` 不纳入第一版
- `lark-cli` 全局软依赖，`MarkItDown` 仅对需转换格式按路径做软依赖检测
- `MarkItDown` 的产物语义是 Markdown，而不是泛化的 plain text
- 成功返回最小结果：`artifact_path`、`ingest_kind`、可选 `title`
- 失败直接抛出带稳定 `code` 的 LLM 友好异常
- 第一版内部模块先合并为少量文件，不为未来扩展提前拆碎
- 自动化测试只覆盖高价值边界

该设计足以支撑后续实现计划，不需要再为第一版引入双后端、自动安装、自动认证修复或超出当前业务边界的扩展能力。
