"""Template CLI: create an app-owned Feishu folder."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from client import create_client
from config import load_config_from_env


def main() -> int:
    name = (sys.argv[1] if len(sys.argv) > 1 else "App-Test-Folder").strip()
    name = name or "App-Test-Folder"
    parent = os.environ.get("FEISHU_DRIVE_CREATE_PARENT_TOKEN", "").strip()

    config = load_config_from_env()
    if not config.feishu_app_id or not config.feishu_app_secret:
        print("请先配置 FEISHU_APP_ID / FEISHU_APP_SECRET", file=sys.stderr)
        return 2

    client = create_client(config)
    try:
        data = client.create_folder(name, parent_folder_token=parent)
    except NotImplementedError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return 1

    if data.get("code") != 0:
        print(data, file=sys.stderr)
        return 1

    inner = data.get("data") or {}
    token = inner.get("token")
    url = inner.get("url")
    print(f"token={token}")
    print(f"url={url}")
    print()
    print("可将下列行写入 .env 供后续 folder subscribe 使用：")
    print(f"FEISHU_SUBSCRIBE_FOLDER_TOKEN={token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
