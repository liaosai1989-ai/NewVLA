from webhook_cursor_executor.feishu_folder_resolve import (
    _feishu_api_ok,
    _file_token_in_list,
)


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
