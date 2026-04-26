"""Minimal config skeleton for the Feishu app-folder mini package."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class AppFolderConfig:
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_subscribe_folder_token: str = ""
    feishu_user_open_id: str = ""
    feishu_user_access_token: str = ""
    feishu_folder_link_share_entity: str = "tenant_editable"
    feishu_folder_external_access: str = "closed"


def load_config_from_env(env: Mapping[str, str] | None = None) -> AppFolderConfig:
    source = env or os.environ
    return AppFolderConfig(
        feishu_app_id=(source.get("FEISHU_APP_ID", "") or "").strip(),
        feishu_app_secret=(source.get("FEISHU_APP_SECRET", "") or "").strip(),
        feishu_subscribe_folder_token=(
            source.get("FEISHU_SUBSCRIBE_FOLDER_TOKEN", "") or ""
        ).strip(),
        feishu_user_open_id=(source.get("FEISHU_USER_OPEN_ID", "") or "").strip(),
        feishu_user_access_token=(source.get("FEISHU_USER_ACCESS_TOKEN", "") or "").strip(),
        feishu_folder_link_share_entity=(
            source.get("FEISHU_FOLDER_LINK_SHARE_ENTITY", "") or "tenant_editable"
        ).strip()
        or "tenant_editable",
        feishu_folder_external_access=(
            source.get("FEISHU_FOLDER_EXTERNAL_ACCESS", "") or "closed"
        ).strip()
        or "closed",
    )
