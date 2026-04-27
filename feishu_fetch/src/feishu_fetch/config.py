from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_dotenv_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    raw = path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k:
            out[k] = v
    return out


def _resolve_env_file(env_file: Path | None, environ: dict[str, str]) -> Path:
    if env_file is not None:
        return env_file.resolve()
    raw = (environ.get("FEISHU_FETCH_ENV_FILE") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.cwd() / ".env").resolve()


@dataclass(frozen=True)
class FeishuFetchSettings:
    request_timeout_seconds: float
    feishu_app_id: str
    env_file: Path
    workspace_root: Path


def load_feishu_fetch_settings(
    *,
    env_file: Path | None = None,
    environ: dict[str, str] | None = None,
) -> FeishuFetchSettings:
    env = environ if environ is not None else os.environ
    env_path = _resolve_env_file(env_file, env)
    workspace_root = env_path.parent
    values = _parse_dotenv_file(env_path)
    if "LARK_CLI_COMMAND" in values:
        raise ValueError(
            "根 .env 含已废弃键 LARK_CLI_COMMAND，请整行删除；"
            "feishu_fetch 子进程只使用命令名 lark-cli（由 facade 直接调用，不经 .env 配置）"
        )
    raw_timeout = (values.get("FEISHU_REQUEST_TIMEOUT_SECONDS") or "60").strip()
    feishu_app_id = (values.get("FEISHU_APP_ID") or "").strip()
    if not feishu_app_id:
        raise ValueError(
            "根 .env 缺少 FEISHU_APP_ID，无法与 lark-cli config show 的 appId 做一致性比对"
        )
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise ValueError("FEISHU_REQUEST_TIMEOUT_SECONDS 不是合法数字") from exc
    if timeout <= 0 or timeout != timeout:  # nan
        raise ValueError("FEISHU_REQUEST_TIMEOUT_SECONDS 必须是正数")
    return FeishuFetchSettings(
        request_timeout_seconds=timeout,
        feishu_app_id=feishu_app_id,
        env_file=env_path,
        workspace_root=workspace_root,
    )
