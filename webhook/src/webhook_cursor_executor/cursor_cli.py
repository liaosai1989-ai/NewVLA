from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Headless 管线必须使用 **Cursor Agent CLI**（官方安装后命令名为 `agent`），
# 与桌面应用启动器 `cursor`（Electron）不是同一个可执行文件。
# 见 https://cursor.com/docs/cli/overview — Windows: irm 'https://cursor.com/install?win32=true' | iex
_AGENT_CLI = "agent"


def _resolve_agent_exe() -> str:
    w = shutil.which(_AGENT_CLI)
    if w:
        return w
    raise FileNotFoundError(
        f"PATH 中未找到命令 {_AGENT_CLI!r}（Cursor Agent CLI）。"
        f"桌面版 `cursor` 不能替代：webhook 需要 `agent -p` 非交互模式。"
        f"安装见 Cursor 文档 CLI 章节，安装后把 agent 所在目录加入运行 webhook/RQ 的账户 PATH。"
    )


@dataclass
class CursorRunResult:
    exit_code: int
    status: str
    summary: str


def ensure_max_mode_config(*, config_path: Path) -> None:
    payload: dict = {}
    if config_path.exists():
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["maxMode"] = True
    model = payload.get("model") or {}
    model["maxMode"] = True
    payload["model"] = model
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def launch_cursor_agent(
    *,
    cwd: Path,
    prompt_text: str,
    model: str,
    timeout_seconds: int,
) -> CursorRunResult:
    exe = _resolve_agent_exe()
    completed = subprocess.run(
        [
            exe,
            "-p",
            "--force",
            "--trust",
            "--workspace",
            str(cwd.resolve()),
            "--model",
            model,
            prompt_text,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    return CursorRunResult(
        exit_code=completed.returncode,
        status="succeeded" if completed.returncode == 0 else "failed",
        summary=completed.stdout.strip() or completed.stderr.strip(),
    )
