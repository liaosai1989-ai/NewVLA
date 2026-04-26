"""Template CLI: grant a user access to the app-owned folder."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from client import create_client
from config import load_config_from_env

TRUTHY = {"1", "true", "yes"}


def main() -> int:
    config = load_config_from_env()
    folder = config.feishu_subscribe_folder_token
    open_id = config.feishu_user_open_id
    if not folder or not open_id:
        print(
            "请先配置 FEISHU_SUBSCRIBE_FOLDER_TOKEN 与 FEISHU_USER_OPEN_ID",
            file=sys.stderr,
        )
        return 2
    if not config.feishu_app_id or not config.feishu_app_secret:
        print("请先配置 FEISHU_APP_ID / FEISHU_APP_SECRET", file=sys.stderr)
        return 2

    perm = os.environ.get("FEISHU_FOLDER_GRANT_PERM", "").strip() or "full_access"
    use_user_token = (
        os.environ.get("FEISHU_FOLDER_GRANT_USE_USER_TOKEN", "").strip().lower() in TRUTHY
    )
    user_token = config.feishu_user_access_token if use_user_token else None
    if use_user_token and not user_token:
        print("已启用用户令牌模式，但 FEISHU_USER_ACCESS_TOKEN 为空", file=sys.stderr)
        return 2

    client = create_client(config)
    try:
        data = client.grant_user_access(
            folder,
            open_id,
            perm=perm,
            user_access_token=user_token,
        )
    except NotImplementedError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return 1

    if data.get("code") != 0:
        print(data, file=sys.stderr)
        return 1

    print("ok", data.get("data", {}).get("member", data.get("data")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
