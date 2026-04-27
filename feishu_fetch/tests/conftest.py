from __future__ import annotations

from pathlib import Path


def write_root_dotenv(
    directory: Path,
    *,
    feishu_app_id: str = "cli_test",
    timeout_s: int | float = 60,
) -> Path:
    """在 directory 下写最小根 .env，与 load_feishu_fetch_settings(env_file=...) 联用。"""
    env_file = directory / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"FEISHU_REQUEST_TIMEOUT_SECONDS={timeout_s}",
                f"FEISHU_APP_ID={feishu_app_id}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return env_file
