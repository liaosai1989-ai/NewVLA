from __future__ import annotations

import sys

import httpx

import feishu_onboard.verify_delegate as vd_mod
from feishu_onboard.feishu_client import CREATE_FOLDER_URL
from feishu_onboard.verify_delegate import run_verify_delegate


def test_cli_dispatches_verify_delegate(monkeypatch) -> None:
    seen: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        seen.append(list(argv or []))
        return 0

    monkeypatch.setattr(vd_mod, "main", fake_main)
    monkeypatch.setattr(sys, "argv", ["feishu-onboard", "verify-delegate", "--open-id", "ou_x"])
    from feishu_onboard import cli

    assert cli.main() == 0
    assert seen == [["--open-id", "ou_x"]]


def test_run_verify_delegate_ok(tmp_path) -> None:
    envp = tmp_path / ".env"
    envp.write_text(
        "FEISHU_APP_ID=cli_x\nFEISHU_APP_SECRET=sec\n",
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "tenant_access_token" in u:
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t0", "expire": 60})
        if str(request.url).startswith(CREATE_FOLDER_URL):
            return httpx.Response(
                200,
                json={"code": 0, "data": {"token": "fld_verify", "url": "https://f.example/d"}},
            )
        if "permissions" in u and "members" in u and "public" not in u:
            return httpx.Response(200, json={"code": 0, "data": {}})
        return httpx.Response(500, text=u)

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=30.0)
    r = run_verify_delegate("ou_abc", env_path=envp, httpx_client=client, name_prefix="t")
    assert r.ok
    assert r.folder_token == "fld_verify"
    assert r.message is None
    assert r.folder_url == "https://f.example/d"


def test_run_verify_delegate_missing_secret(tmp_path) -> None:
    envp = tmp_path / ".env"
    envp.write_text("FEISHU_APP_ID=onlyid\n", encoding="utf-8")
    r = run_verify_delegate("ou_x", env_path=envp)
    assert not r.ok
    assert "FEISHU" in (r.message or "")
