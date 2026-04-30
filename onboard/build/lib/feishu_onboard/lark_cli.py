from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def lark_config_init_excerpt_for_failure(
    proc: subprocess.CompletedProcess[bytes],
) -> str:
    """子进程已失败时，拼一段便于排障的短文案（截断，避免长日志当默认输出）。"""
    rc = proc.returncode
    err_s = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    out_s = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    line = f"lark 子进程失败: 退出码={rc}"
    if err_s:
        if len(err_s) > 1200:
            err_s = err_s[:1200] + "…"
        line = f"{line} | stderr: {err_s}"
    elif out_s:
        if len(out_s) > 800:
            out_s = out_s[:800] + "…"
        line = f"{line} | stdout: {out_s}"
    return line


def _resolve_lark_cli_exe(lark_command: str) -> str:
    """只通过 PATH 解析命令名（默认 `lark-cli`），再交给 subprocess。

    Windows 下对裸名 `lark-cli` 与 PowerShell 的解析可能不一致，故统一用 `shutil.which`。
    不支持在应用配置里写死可执行文件路径；PATH 由运行环境（系统/用户/终端）提供。
    """
    c = lark_command.strip()
    if not c:
        raise FileNotFoundError("lark_command 为空")
    w = shutil.which(c)
    if w:
        return w
    raise FileNotFoundError(
        f"PATH 中未找到命令 {c!r}。请安装飞书 lark 命令行工具（常见全局名为 lark-cli），"
        f"将可执行文件所在目录加入用户或系统 PATH 后重开终端。"
    )


def lark_config_init(
    cwd: Path,
    app_id: str,
    app_secret: str,
    *,
    lark_command: str = "lark-cli",
) -> subprocess.CompletedProcess[bytes]:
    exe = _resolve_lark_cli_exe(lark_command)
    return subprocess.run(
        [exe, "config", "init", "--app-id", app_id, "--app-secret-stdin"],
        input=app_secret.encode("utf-8"),
        cwd=cwd,
        capture_output=True,
    )


def lark_config_show_verify_app_id(
    cwd: Path,
    expected_app_id: str,
    *,
    lark_command: str = "lark-cli",
) -> None:
    # @larksuite/cli 1.0.19：`config show` 无 --json；stdout 默认可 json.loads（与 `config show --help` 仅含 -h 一致）。
    exe = _resolve_lark_cli_exe(lark_command)
    proc = subprocess.run(
        [exe, "config", "show"],
        cwd=cwd,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise ValueError(
            f"lark 子进程失败: 退出码={proc.returncode}"
        )
    try:
        data = json.loads(proc.stdout.decode("utf-8").strip() or "{}")
    except json.JSONDecodeError as e:
        raise ValueError("lark config show 输出非合法 JSON") from e
    aid = data.get("appId") or data.get("app_id")
    if aid != expected_app_id:
        raise ValueError(
            f"lark appId 与 FEISHU_APP_ID 不一致: 期望 {expected_app_id!r} 得到 {aid!r}"
        )
