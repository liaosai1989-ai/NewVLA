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

关于 `AGENTS.md` 与 `rules/`：`AGENTS.md` 及 Cursor 规则通常会随 CLI 会话注入；若你认为上下文已足够，**可以不再打开文件通读**，由你自行判断。

以下为本轮 webhook 写入的内容，**务必先读取**（不要仅凭摘要推断）：
- `.cursor_task/{run_id}/task_context.json`
- 其中 `qa_rule_file` 指向的 QA 规则文件

任务要求：
- 这是一次自动触发任务，不要假设用户会补充额外上下文。
- `dataset_id`、上传目标与业务步骤以 **`task_context.json` 及上述 QA 规则** 为准，不要从其它静态文档猜测 Dify 路由。
- 如果规则要求调用工具，按规则执行。
- 不要伪造工具结果。
- 不要从仓库文档或静态规则中推断 Dify 目标。
- `dataset_id` 必须以 `task_context.json` 中的显式注入值为准。
- 最终结果需要上传到 `task_context.json` 中指定的 Dify `dataset_id`。
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
