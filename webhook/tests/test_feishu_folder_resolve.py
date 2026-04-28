from webhook_cursor_executor.feishu_folder_resolve import (
    _feishu_api_ok,
    _file_token_in_list,
    resolve_folder_route,
)
from webhook_cursor_executor.settings import FolderRoute, PipelineWorkspace, RoutingConfig


def test_feishu_api_ok_treats_zero_as_success():
    assert _feishu_api_ok({"code": 0})
    assert _feishu_api_ok({"code": "0"})
    assert not _feishu_api_ok({"code": 1})
    assert not _feishu_api_ok({})


def test_file_token_in_list_matches_direct_token():
    payload = {
        "code": 0,
        "data": {
            "files": [
                {"token": "docx_real", "type": "docx", "parent_token": "fld1"},
            ]
        },
    }
    assert _file_token_in_list(payload, "docx_real")
    assert not _file_token_in_list(payload, "other")


def test_file_token_in_list_matches_shortcut_target_token():
    """drive.file.edit_v1 的 file_token 为真实文档；夹内可能是 shortcut 行。"""
    payload = {
        "code": 0,
        "data": {
            "files": [
                {
                    "token": "nod_shortcut_wrapper",
                    "type": "shortcut",
                    "parent_token": "fld1",
                    "shortcut_info": {
                        "target_token": "Rz5EdOgg1oQzeSx2o05cLRfTnrh",
                        "target_type": "docx",
                    },
                },
            ]
        },
    }
    assert _file_token_in_list(payload, "Rz5EdOgg1oQzeSx2o05cLRfTnrh")
    # 列表行自身 token（快捷方式壳）仍可命中，与事件若带壳 token 一致
    assert _file_token_in_list(payload, "nod_shortcut_wrapper")


def test_resolve_folder_route_returns_dify_target_key_from_config():
    cfg = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(path="C:\\ws", cursor_timeout_seconds=3600),
        folder_routes=[
            FolderRoute(
                folder_token="ft_route_a",
                qa_rule_file="rules/q.md",
                dataset_id="ds1",
                dify_target_key="PROD_A",
            )
        ],
    )
    hit = resolve_folder_route(cfg, "ft_route_a")
    assert hit is not None
    assert hit.dify_target_key == "PROD_A"
    assert hit.folder_token == "ft_route_a"


def test_resolve_folder_route_default_dify_target_key_when_omitted():
    cfg = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(path="C:\\ws", cursor_timeout_seconds=3600),
        folder_routes=[
            FolderRoute(
                folder_token="ft_b",
                qa_rule_file="rules/q.md",
                dataset_id="ds1",
            )
        ],
    )
    hit = resolve_folder_route(cfg, "ft_b")
    assert hit is not None
    assert hit.dify_target_key == "DEFAULT"
