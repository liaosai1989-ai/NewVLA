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
    return f"""你正在处理一次由飞书 webhook 自动触发的任务。

任务目标：
- 按当前工作区约定完成该文档的后续处理流程。
- 本次处理对象为：`document_id={context["document_id"]}`。
- 触发事件类型为：`{context["event_type"]}`。

关于 `AGENTS.md` 与 `rules/`：`AGENTS.md` 已由工作区规则注入；**除非你认为未加载，否则不必再打开** `AGENTS.md` 通读。

以下为本轮 webhook 写入的内容，**务必先读取**（不要仅凭摘要推断）：
- `.cursor_task/{run_id}/task_context.json`
- 其中 `qa_rule_file` 指向的 QA 规则文件

任务要求：
- 这是一次自动触发任务，不要假设用户会补充额外上下文。
- `dataset_id`、上传目标与业务步骤以 **`task_context.json` 及上述 QA 规则** 为准，不要从其它静态文档猜测 Dify 路由。
- 如果规则要求调用工具，按规则执行。
- 不要伪造工具结果。
- 不要从仓库文档或静态规则中推断 Dify 目标。
- `dify_target_key` 与 `ingest_kind` 以 **`task_context.json` 中的值为权威**；与执行工作区根 `.env` 里 `DIFY_TARGET_<KEY>_*` 的解析由工具封装完成，勿自行改键。
- `dataset_id` 必须以 `task_context.json` 中的显式注入值为准。
- 当 `dataset_id_is_placeholder` 为 true（或 `dataset_id` 为已知占位模式）时：**只**生成并校验上传用 CSV（或规则要求的校验步骤），**不要**对真实 Dify 数据集发起上传。
- 非占位任务：最终结果需要上传到 `task_context.json` 中指定的 Dify `dataset_id`。

`feishu_fetch`（若需调用）：
- **`ingest_kind`**：生产路径上 **必须** 出现在 `task_context.json`（`cloud_docx` 或 `drive_file`），由 webhook 在解析与路由完成后写入；构造 `FeishuFetchRequest` 时 **必须** 与其一致，不得另猜。若缺失则视为任务注入不完整，停止并写明原因（勿自行用 `event_type`/规则顶替）。**仅**手工/bootstrap 演示 JSON 可在文档中约定例外，且须在规则或任务单中显式说明。
- **`output_dir`**：**不在 JSON 里注入**。**强制**使用相对工作区根的 `.cursor_task/{run_id}/outputs`（已由本轮创建）；`feishu_fetch` 等工具仍须满足输出路径落在工作区根内。
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
