import json

import pytest

from feishu_fetch.lark_env import app_id_from_config_show_payload, parse_config_show_json


def test_parse_minimal_config_show() -> None:
    payload = {"appId": "cli_xxx", "brand": "Feishu"}
    stdout = json.dumps(payload, ensure_ascii=False)
    data = parse_config_show_json(stdout)
    assert app_id_from_config_show_payload(data) == "cli_xxx"


def test_app_id_alias() -> None:
    payload = {"app_id": "cli_yyy"}
    assert app_id_from_config_show_payload(payload) == "cli_yyy"


def test_empty_app_id_fails() -> None:
    with pytest.raises(ValueError):
        app_id_from_config_show_payload({})
