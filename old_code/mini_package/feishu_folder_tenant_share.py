"""Template CLI: try to set folder sharing inside the tenant."""

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
    config = load_config_from_env()
    folder_token = (
        sys.argv[1] if len(sys.argv) > 1 else config.feishu_subscribe_folder_token
    ).strip()
    if not folder_token:
        print(
            "请传入 folder_token，或配置 FEISHU_SUBSCRIBE_FOLDER_TOKEN",
            file=sys.stderr,
        )
        return 2
    if not config.feishu_app_id or not config.feishu_app_secret:
        print("请先配置 FEISHU_APP_ID / FEISHU_APP_SECRET", file=sys.stderr)
        return 2

    link = (
        os.environ.get("FEISHU_FOLDER_LINK_SHARE_ENTITY", "").strip()
        or config.feishu_folder_link_share_entity
        or "tenant_editable"
    )
    external = (
        os.environ.get("FEISHU_FOLDER_EXTERNAL_ACCESS", "").strip()
        or config.feishu_folder_external_access
        or "closed"
    )

    client = create_client(config)
    try:
        data = client.patch_folder_public(
            folder_token,
            link_share_entity=link,
            external_access_entity=external,
        )
    except NotImplementedError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return 1

    if data.get("code") != 0:
        print(data, file=sys.stderr)
        print("若 folder 场景不支持 public patch，请改走协作者授权方案。", file=sys.stderr)
        return 1

    print("ok", data.get("data", {}).get("permission_public", data.get("data")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
