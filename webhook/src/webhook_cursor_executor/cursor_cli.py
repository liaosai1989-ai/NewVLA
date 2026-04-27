from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# 固定命令名，仅由 PATH 解析（不经 .env / 配置写可执行路径）；与 onboard `lark-cli` 约定一致。
_CURSOR_CLI = "cursor"


def _resolve_cursor_exe() -> str:
    w = shutil.which(_CURSOR_CLI)
    if w:
        return w
    raise FileNotFoundError(
        f"PATH 中未找到命令 {_CURSOR_CLI!r}。请安装 Cursor CLI，"
        f"将可执行文件所在目录加入用户或系统 PATH 后重开服务/终端。"
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
    exe = _resolve_cursor_exe()
    completed = subprocess.run(
        [exe, "agent", "--model", model, prompt_text],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return CursorRunResult(
        exit_code=completed.returncode,
        status="succeeded" if completed.returncode == 0 else "failed",
        summary=completed.stdout.strip() or completed.stderr.strip(),
    )
