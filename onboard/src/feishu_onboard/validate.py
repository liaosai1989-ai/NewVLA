from __future__ import annotations

import re
from pathlib import Path

from vla_env_contract import dify_group_keys

_RE_ENV_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
_MAX_TOKEN_LEN = 256


def is_safe_env_key(name: str) -> bool:
    return bool(_RE_ENV_KEY.match(name.strip()))


def validate_route_key(route_key: str) -> str:
    s = route_key.strip().upper()
    if not is_safe_env_key(s):
        raise ValueError("route_key 必须匹配 ^[A-Z][A-Z0-9_]*$")
    return s


def validate_dify_target_key(dify_target_key: str) -> str:
    s = dify_target_key.strip().upper()
    if not is_safe_env_key(s):
        raise ValueError("dify_target_key 必须匹配 ^[A-Z][A-Z0-9_]*$")
    return s


def validate_qa_rule_file(relative: str) -> str:
    p = relative.strip().replace("\\", "/")
    if p.startswith("/") or Path(p).is_absolute():
        raise ValueError("qa_rule_file 禁止绝对路径")
    parts = [x for x in p.split("/") if x != ""]
    if ".." in parts:
        raise ValueError("qa_rule_file 禁止 ..")
    if not parts:
        raise ValueError("qa_rule_file 不能为空")
    under_rules = parts[0] == "rules"
    under_prompts_rules = (
        len(parts) >= 2 and parts[0] == "prompts" and parts[1] == "rules"
    )
    if not (under_rules or under_prompts_rules):
        raise ValueError(
            "qa_rule_file 必须为 rules/ 或 prompts/rules/ 下相对路径，禁止 .."
        )
    return p


def validate_parent_folder_token(token: str) -> str:
    t = token.strip()
    if len(t) > _MAX_TOKEN_LEN:
        raise ValueError("parent_folder_token 过长")
    if not t:
        return ""
    for ch in t:
        if ch in "\r\n\x00":
            raise ValueError("parent_folder_token 含非法字符")
    return t


def dify_group_present(env: dict[str, str], dify_target_key: str) -> None:
    for key in dify_group_keys(dify_target_key):
        v = (env.get(key) or "").strip()
        if not v:
            raise ValueError(
                f"根 .env 缺少完整 Dify 组: 缺少非空 {key}（dify_target_key={dify_target_key}）"
            )
