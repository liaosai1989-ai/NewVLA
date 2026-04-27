from __future__ import annotations

import json
from typing import Any


def parse_config_show_json(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        raise ValueError("config show 无输出")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("config show 顶层不是 JSON 对象")
    return data


def app_id_from_config_show_payload(data: dict[str, Any]) -> str:
    aid = data.get("appId") or data.get("app_id")
    s = str(aid).strip() if aid is not None else ""
    if not s:
        raise ValueError("config show 中缺少非空 appId")
    return s
