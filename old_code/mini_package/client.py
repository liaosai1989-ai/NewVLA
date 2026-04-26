"""Placeholder client skeleton for the Feishu app-folder mini package."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Protocol

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from config import AppFolderConfig


class FeishuAppFolderClient(Protocol):
    def create_folder(
        self,
        name: str,
        parent_folder_token: str = "",
    ) -> dict[str, Any]: ...

    def grant_user_access(
        self,
        folder_token: str,
        open_id: str,
        *,
        perm: str,
        user_access_token: str | None = None,
    ) -> dict[str, Any]: ...

    def patch_folder_public(
        self,
        folder_token: str,
        *,
        link_share_entity: str,
        external_access_entity: str,
    ) -> dict[str, Any]: ...


class PlaceholderFeishuAppFolderClient:
    """Replace this class with your own HTTP/OpenAPI implementation."""

    def __init__(self, config: AppFolderConfig) -> None:
        self._config = config

    def _unimplemented(self, action: str, api_hint: str) -> NotImplementedError:
        return NotImplementedError(
            "Replace PlaceholderFeishuAppFolderClient with your project's Feishu HTTP client. "
            f"Missing action: {action}. Suggested OpenAPI: {api_hint}. "
            "Keep the return value shape compatible with the bundled CLI scripts."
        )

    def create_folder(
        self,
        name: str,
        parent_folder_token: str = "",
    ) -> dict[str, Any]:
        raise self._unimplemented(
            "create_folder(name, parent_folder_token)",
            "POST /open-apis/drive/v1/files/create_folder",
        )

    def grant_user_access(
        self,
        folder_token: str,
        open_id: str,
        *,
        perm: str,
        user_access_token: str | None = None,
    ) -> dict[str, Any]:
        raise self._unimplemented(
            "grant_user_access(folder_token, open_id, perm, user_access_token)",
            "POST /open-apis/drive/v1/permissions/{token}/members",
        )

    def patch_folder_public(
        self,
        folder_token: str,
        *,
        link_share_entity: str,
        external_access_entity: str,
    ) -> dict[str, Any]:
        raise self._unimplemented(
            "patch_folder_public(folder_token, link_share_entity, external_access_entity)",
            "PATCH /open-apis/drive/v1/permissions/{token}/public",
        )


def create_client(config: AppFolderConfig) -> FeishuAppFolderClient:
    return PlaceholderFeishuAppFolderClient(config)
