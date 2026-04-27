import pytest

from feishu_onboard.env_contract import dify_group_keys, required_dify_group_suffixes
from feishu_onboard.validate import dify_group_present


def test_dify_group_complete() -> None:
    env = {
        "DIFY_TARGET_X_API_BASE": "https://a/v1",
        "DIFY_TARGET_X_API_KEY": "k",
        "DIFY_TARGET_X_HTTP_VERIFY": "true",
        "DIFY_TARGET_X_TIMEOUT_SECONDS": "10",
    }
    dify_group_present(env, "X")
    for suf in required_dify_group_suffixes():
        assert f"DIFY_TARGET_X_{suf}" in dify_group_keys("X")


def test_dify_group_missing_key_raises() -> None:
    env = {"DIFY_TARGET_X_API_BASE": "https://a/v1"}
    with pytest.raises(ValueError, match="DIFY_TARGET_X_API_KEY|缺少"):
        dify_group_present(env, "X")


def test_dify_group_empty_value_raises() -> None:
    env = {
        "DIFY_TARGET_X_API_BASE": "https://a/v1",
        "DIFY_TARGET_X_API_KEY": "",
        "DIFY_TARGET_X_HTTP_VERIFY": "true",
        "DIFY_TARGET_X_TIMEOUT_SECONDS": "10",
    }
    with pytest.raises(ValueError):
        dify_group_present(env, "X")
