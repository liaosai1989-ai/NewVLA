from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TaskBundlePaths:
    run_dir: Path
    prompt_path: Path
    context_path: Path
    outputs_dir: Path


def build_task_prompt(context: dict[str, Any]) -> str:
    run_id = context["run_id"]
    qa_rule_file = context["qa_rule_file"]
    workspace_path = context["workspace_path"]
    dataset_id = context["dataset_id"]
    dataset_id_is_placeholder = context["dataset_id_is_placeholder"]
    dify_target_key = context["dify_target_key"]
    ingest_kind = context["ingest_kind"]
    resource_plane = context["resource_plane"]
    event_id = context["event_id"]
    folder_token = context["folder_token"]
    snapshot_version = context["snapshot_version"]
    return f"""你正在处理一次**系统自动派发、已落盘到本目录**的单次文档任务。

任务目标：
- 按当前工作区约定完成该文档的后续处理流程。
- 本次处理对象为：`document_id={context["document_id"]}`。
- 事件类型字段为：`{context["event_type"]}`。

**本轮任务目录**（唯一会话根；**禁止**与工作区内其它 `.cursor_task/<其它 run_id>/` 混读、混写）：
- 根路径：**`.cursor_task/{run_id}/`**
- **`task_context.json`、本目录下 `task_prompt.md`、`outputs/`** 均属本轮；凡落盘、读本任务产物，**只认此路径下**（含子路径），**不要**打开或引用其它 `run_id` 目录当本次任务。

工作区根路径（解析所有相对路径时用此根；与 `task_context.json` 内 `workspace_path` 一致）：`{workspace_path}`

关于 `AGENTS.md` 与 `rules/`：`AGENTS.md` 已由工作区规则注入；**除非你认为未加载，否则不必再打开** `AGENTS.md` 通读。

本轮关键 ID（与 **`task_context.json` 互证**；勿改用他轮或手写值）：
- `run_id`：**`{run_id}`**
- `event_id`：**`{event_id}`**
- `folder_token`：**`{folder_token}`**
- `snapshot_version`：**{snapshot_version}**

**任务编排指导**（先做：用 **`TodoWrite`** 生成可勾选清单；**清单措辞须指向下列真实路径与字段**，禁止只写泛泛「读配置」「上传」而看不到路径。）

### Task 1: 读取本轮注入与 QA 规则

- 打开并理解 **`.cursor_task/{run_id}/task_context.json`**（唯一配置源）。
- 打开并遵守（相对**工作区根**）**`{qa_rule_file}`**；**不要**从其它 `rules/` 或未在 `qa_rule_file` 列出的文件顶替。

### Task 2: 按需拉取文档与中间产物

- 本轮约定的资源面：**`ingest_kind={ingest_kind}`**，**`resource_plane={resource_plane}`**；构造请求时与此二字段一致。
- 凡落盘、工具输出：**只写入** **`.cursor_task/{run_id}/outputs/`**（及该目录下子路径）；勿写到其它 `run_id` 或工作区根散落目录。

### Task 3: 读取 QA 并完成抽取、生成上传用 CSV

- 遵循 **`{qa_rule_file}`**、`rules/qa/base/output_contract.mdc`（及 `rules/00_qa_rule_usage.mdc` 中与输出相关的索引）从已拉取正文完成 QA 抽取，写出 **UTF-8**、表头与列符合 **`output_contract`** 的 CSV。
- **存放位置与命名（唯一合法）**：**`.cursor_task/{run_id}/outputs/{run_id}.csv`** — 文件名 **`{run_id}.csv`** 须与同目录 **`task_context.json` 的 `run_id`** 逐字相同；**禁止**用 `qa.csv`、`upload.csv` 等顶替本轮最终上传件。

### Task 4: QA 质检；不合格则改 CSV 直至合格

- 读取并按 **`rules/qa/base/quality_checks.mdc`**（及 **`{qa_rule_file}`** 中指向的质检要求）检查 **`.cursor_task/{run_id}/outputs/{run_id}.csv`**。
- 不合格：只在本轮路径上**反复修改同一文件**直至质检通过；**不要**换新文件名当自己通过。

### Task 5: 上传 Dify

- 本轮 Dify 绑定（与 **`task_context.json` 一致即准，勿改）：**`dify_target_key={dify_target_key}`**，**`dataset_id={dataset_id}`**，**`dataset_id_is_placeholder={dataset_id_is_placeholder}`**。
- 使用 **`dify_upload`**（如 **`resolve_dify_target`** + 工作区 **`.env`**）解析目标，对 **`.cursor_task/{run_id}/outputs/{run_id}.csv`** 执行上传或其它规则允许的动作；**禁止**手拼密钥、自拟 **`api_base`/`api_key`**。
- **是否对真实知识库上传**仅依 **`task_context.json` + QA 规则**，勿自选策略。

### Task 6: 任务结束写运行日志

- 在本轮目录 **`.cursor_task/{run_id}/`** 编写 **`run_completion.log`**（UTF-8）：至少 **`run_id`**、结束时间、**`succeeded`/`failed`/`stopped`**、关键步骤摘要；若有 Dify 操作则 **`document_id`/`batch`** 或错误摘要。**禁止**写入密钥原文。

任务要求（全局，**不**重复上文 Task；冲突时仍以 **`task_context.json`** 与同轮 **`task_prompt.md`** 的步骤为准）：
- **不要假设**会有人类用户在本轮中补充口述上下文。
- **不要**伪造工具结果。
- 工具调用：**按 QA 规则与 Task 编排**执行；路由与目标实例**不要**从仓库泛化 README、`rules/` 里未挂载到 **`qa_rule_file`** 的条文去猜 Dify/飞书面。

`feishu_fetch`（仅在拉取链路需要时）：**`ingest_kind`/`resource_plane` 与同目录 `task_context.json`、与 Task 2 一致**。资源面：`cloud_docx`≈云文档 OpenAPI，`drive_file`≈云盘；字面路径 ``/docx/{{document_id}}`` / ``/file/{{file_token}}`` **仅作对照**，须与 JSON 字段一致，**勿**自改 ingest 语义。缺字段或与 JSON 矛盾：**停止**并说明。**落盘目录**参见 Task 2（**不向 JSON 索要 `output_dir` 字段**）。
"""


def write_task_bundle(
    *,
    workspace_path: Path,
    run_id: str,
    context: dict[str, Any],
) -> TaskBundlePaths:
    run_dir = workspace_path / ".cursor_task" / run_id
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = run_dir / "task_prompt.md"
    context_path = run_dir / "task_context.json"
    prompt_path.write_text(build_task_prompt(context), encoding="utf-8")
    context_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return TaskBundlePaths(
        run_dir=run_dir,
        prompt_path=prompt_path,
        context_path=context_path,
        outputs_dir=outputs_dir,
    )
