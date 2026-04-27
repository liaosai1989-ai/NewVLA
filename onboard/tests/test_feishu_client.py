import json

import httpx

from feishu_onboard.feishu_client import (
    CREATE_FOLDER_URL,
    DRIVE_V1_FILE_SUBSCRIBE_TMPL,
    DRIVE_V1_PERMISSION_MEMBERS_TMPL,
    EXPLORER_V2_CREATE_FOLDER_TMPL,
    FeishuOnboardClient,
    ROOT_FOLDER_META_URL,
    fetch_tenant_access_token,
)


def test_tenant_token(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"code": 0, "tenant_access_token": "t0", "expire": 3600},
    )
    t = fetch_tenant_access_token("id", "sec")
    assert t == "t0"


def test_create_folder_empty_parent_tries_string_first(httpx_mock) -> None:
    httpx_mock.add_response(
        url=CREATE_FOLDER_URL,
        json={
            "code": 0,
            "data": {"token": "fldx", "url": "https://x"},
        },
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    r = c.create_folder("n", parent_folder_token="")
    assert r["folder_token"] == "fldx"
    reqs = httpx_mock.get_requests()
    assert len(reqs) == 1
    post = reqs[0]
    req = post[0] if isinstance(post, tuple) else post
    assert req.method == "POST"
    body = json.loads(req.content.decode("utf-8"))
    assert body == {"name": "n", "folder_token": ""}


def test_create_folder_empty_parent_fallback_on_10003(httpx_mock) -> None:
    httpx_mock.add_response(
        url=CREATE_FOLDER_URL,
        json={"code": 10003, "msg": "invalid param"},
    )
    httpx_mock.add_response(
        method="GET",
        url=ROOT_FOLDER_META_URL,
        json={"code": 0, "data": {"token": "nodroot", "id": "1", "user_id": "2"}},
    )
    httpx_mock.add_response(
        url=CREATE_FOLDER_URL,
        json={
            "code": 0,
            "data": {"token": "fldx", "url": "https://x"},
        },
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    r = c.create_folder("TrustedDataSpace", "")
    assert r["folder_token"] == "fldx"
    reqs = httpx_mock.get_requests()
    assert len(reqs) == 3
    r0 = reqs[0][0] if isinstance(reqs[0], tuple) else reqs[0]
    assert json.loads(r0.content.decode("utf-8")) == {
        "name": "TrustedDataSpace",
        "folder_token": "",
    }
    r2 = reqs[2][0] if isinstance(reqs[2], tuple) else reqs[2]
    assert json.loads(r2.content.decode("utf-8")) == {
        "name": "TrustedDataSpace",
        "folder_token": "nodroot",
    }


def test_create_folder_empty_parent_third_hop_explorer_v2(httpx_mock) -> None:
    httpx_mock.add_response(
        url=CREATE_FOLDER_URL,
        json={"code": 10003, "msg": "invalid param"},
    )
    httpx_mock.add_response(
        method="GET",
        url=ROOT_FOLDER_META_URL,
        json={"code": 0, "data": {"token": "nodroot", "id": "1", "user_id": "2"}},
    )
    httpx_mock.add_response(
        url=CREATE_FOLDER_URL,
        json={"code": 10003, "msg": "invalid param"},
    )
    explorer_url = EXPLORER_V2_CREATE_FOLDER_TMPL.format(folder_token="nodroot")
    httpx_mock.add_response(
        url=explorer_url,
        json={"code": 0, "data": {"token": "fld_explorer", "url": "https://x"}},
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    r = c.create_folder("TDS", "")
    assert r["folder_token"] == "fld_explorer"
    assert r["url"] == "https://x"
    reqs = httpx_mock.get_requests()
    assert len(reqs) == 4
    r3 = reqs[3][0] if isinstance(reqs[3], tuple) else reqs[3]
    assert r3.method == "POST"
    assert json.loads(r3.content.decode("utf-8")) == {"title": "TDS"}


def test_add_folder_user_collaborator_ok(httpx_mock) -> None:
    murl = DRIVE_V1_PERMISSION_MEMBERS_TMPL.format(token="fld_f")
    httpx_mock.add_response(
        method="POST",
        url=httpx.URL(murl, params={"type": "folder"}),
        json={"code": 0, "data": {}},
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    ok, err = c.add_folder_user_collaborator(
        "fld_f", member_type="openid", member_id="ou_1", perm="full_access"
    )
    assert ok and err is None
    raw = httpx_mock.get_requests()[0]
    req = raw[0] if isinstance(raw, tuple) else raw
    b = json.loads(req.content.decode("utf-8"))
    assert b == {"member_type": "openid", "member_id": "ou_1", "perm": "full_access"}


def test_add_folder_user_collaborator_api_error(httpx_mock) -> None:
    murl = DRIVE_V1_PERMISSION_MEMBERS_TMPL.format(token="fld_f")
    httpx_mock.add_response(
        method="POST",
        url=httpx.URL(murl, params={"type": "folder"}),
        json={"code": 1063002, "msg": "no access"},
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    ok, err = c.add_folder_user_collaborator(
        "fld_f", member_type="openid", member_id="ou_1", perm="full_access"
    )
    assert not ok
    assert "1063002" in (err or "")


def test_add_folder_user_collaborator_http400_with_json_body(httpx_mock) -> None:
    """飞书对业务错常回 HTTP 400，body 内仍有 code/msg，不得抛成未预期错误。"""
    murl = DRIVE_V1_PERMISSION_MEMBERS_TMPL.format(token="fld_f")
    httpx_mock.add_response(
        method="POST",
        url=httpx.URL(murl, params={"type": "folder"}),
        status_code=400,
        json={"code": 10003, "msg": "invalid param"},
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    ok, err = c.add_folder_user_collaborator(
        "fld_f", member_type="openid", member_id="ou_1", perm="full_access"
    )
    assert not ok
    assert "400" in (err or "")
    assert "10003" in (err or "")


def test_create_folder_with_parent_token(httpx_mock) -> None:
    httpx_mock.add_response(
        url=CREATE_FOLDER_URL,
        json={"code": 0, "data": {"token": "cfld", "url": "https://p"}},
    )
    c = FeishuOnboardClient(httpx.Client(), "tok")
    r = c.create_folder("child", parent_folder_token="fld999")
    assert r["folder_token"] == "cfld"
    raw = httpx_mock.get_requests()[0]
    req = raw[0] if isinstance(raw, tuple) else raw
    assert req.method == "POST"
    body = json.loads(req.content.decode("utf-8"))
    assert body.get("name") == "child"
    assert body.get("folder_token") == "fld999"


def test_subscribe_folder_file_created(httpx_mock) -> None:
    sub_url = (
        f"{DRIVE_V1_FILE_SUBSCRIBE_TMPL.format(token='fld_sub')}"
        "?file_type=folder&event_type=file.created_in_folder_v1"
    )
    httpx_mock.add_response(method="POST", url=sub_url, json={"code": 0, "data": {}})
    c = FeishuOnboardClient(httpx.Client(), "tok")
    c.subscribe_folder_file_created("fld_sub")
    assert len(httpx_mock.get_requests()) == 1
    r = httpx_mock.get_requests()[0]
    req = r[0] if isinstance(r, tuple) else r
    assert "subscribe" in str(req.url)
    assert "file_type=folder" in str(req.url)
    assert "file.created_in_folder_v1" in str(req.url)
