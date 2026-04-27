from __future__ import annotations

# 与 spec §5.4 中 Dify 组一致


def required_dify_group_suffixes() -> tuple[str, ...]:
    return ("API_BASE", "API_KEY", "HTTP_VERIFY", "TIMEOUT_SECONDS")


def dify_group_keys(dify_target_key: str) -> list[str]:
    k = dify_target_key.strip().upper()
    return [f"DIFY_TARGET_{k}_{s}" for s in required_dify_group_suffixes()]


def feishu_folder_group_keys(route_key: str) -> list[str]:
    r = route_key.strip().upper()
    return [
        f"FEISHU_FOLDER_{r}_NAME",
        f"FEISHU_FOLDER_{r}_TOKEN",
        f"FEISHU_FOLDER_{r}_DIFY_TARGET_KEY",
        f"FEISHU_FOLDER_{r}_DATASET_ID",
        f"FEISHU_FOLDER_{r}_QA_RULE_FILE",
    ]


def route_keys_list_key() -> str:
    return "FEISHU_FOLDER_ROUTE_KEYS"
