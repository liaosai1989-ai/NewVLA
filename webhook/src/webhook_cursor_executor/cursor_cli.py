from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


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
    command: str,
    cwd: Path,
    prompt_text: str,
    model: str,
    timeout_seconds: int,
) -> CursorRunResult:
    completed = subprocess.run(
        [command, "agent", "--model", model, prompt_text],
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
