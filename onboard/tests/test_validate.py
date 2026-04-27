import pytest

from feishu_onboard.validate import (
    is_safe_env_key,
    validate_dify_target_key,
    validate_parent_folder_token,
    validate_qa_rule_file,
    validate_route_key,
)


def test_route_key_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="route_key"):
        validate_route_key("1AB")


def test_route_key_ok_normalizes_case() -> None:
    assert validate_route_key("  team_a  ") == "TEAM_A"
    validate_route_key("TEAM_A")


def test_qa_not_under_rules() -> None:
    with pytest.raises(ValueError, match="rules"):
        validate_qa_rule_file("other/qa.mdc")
    with pytest.raises(ValueError, match="rules"):
        validate_qa_rule_file("prompts/other/qa.mdc")


def test_qa_dotdot_rejected() -> None:
    with pytest.raises(ValueError):
        validate_qa_rule_file("rules/../x.mdc")


def test_qa_ok() -> None:
    validate_qa_rule_file("rules/qa/team.mdc")
    validate_qa_rule_file("prompts/rules/qa/folders/folder_rule_template.mdc")


def test_parent_token_empty_ok() -> None:
    validate_parent_folder_token("")


def test_parent_token_too_long() -> None:
    with pytest.raises(ValueError):
        validate_parent_folder_token("a" * 300)


def test_is_safe_env_key() -> None:
    assert is_safe_env_key("TEAM_A1")
    assert not is_safe_env_key("1AB")


def test_dify_target_key_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="dify_target_key"):
        validate_dify_target_key("1AB")


def test_dify_target_key_ok_normalizes_case() -> None:
    assert validate_dify_target_key("  team_a  ") == "TEAM_A"
    assert validate_dify_target_key("TEAM_A") == "TEAM_A"
