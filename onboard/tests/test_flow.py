from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import httpx

from feishu_onboard.flow import OnboardInput, run_onboard

_DELEGATE = "FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID=ou_delegate\n"


def _write_env(
    p,
    extra: str = "",
) -> None:
    lines = [
        "FEISHU_APP_ID=cli_abc",
        "FEISHU_APP_SECRET=sec",
        "DIFY_TARGET_X_API_BASE=https://a/v1",
        "DIFY_TARGET_X_API_KEY=k",
        "DIFY_TARGET_X_HTTP_VERIFY=true",
        "DIFY_TARGET_X_TIMEOUT_SECONDS=10",
    ]
    p.write_text("\n".join(lines) + (extra and "\n" + extra), encoding="utf-8")


def _rules_file(tmp_path) -> None:
    d = tmp_path / "rules" / "qa"
    d.mkdir(parents=True)
    (d / "a.mdc").write_text("k", encoding="utf-8")


def test_missing_delegate_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    _rules_file(tmp_path)
    envp = tmp_path / ".env"
    _write_env(envp)
    r = run_onboard(
        OnboardInput(
            route_key="Z",
            folder_name="F",
            dify_target_key="X",
            dataset_id="d",
            qa_rule_file="rules/qa/a.mdc",
        ),
        env_path=envp,
    )
    assert not r.exit_ok
    assert not r.partial
    assert "FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID" in (r.message or "")


def test_full_success_stage_b(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    _rules_file(tmp_path)
    envp = tmp_path / ".env"
    _write_env(envp, "FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID=ou_test")

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "tenant_access_token" in u:
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t0", "expire": 60})
        if "root_folder/meta" in u:
            return httpx.Response(
                200,
                json={"code": 0, "data": {"token": "nod_root", "id": "1", "user_id": "2"}},
            )
        if "create_folder" in u:
            return httpx.Response(200, json={"code": 0, "data": {"token": "fld_new", "url": "https://f"}})
        if "permissions" in u and "members" in u and "public" not in u:
            return httpx.Response(200, json={"code": 0, "data": {}})
        return httpx.Response(500, text="unhandled " + u)

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=30.0)
    p_run = MagicMock(returncode=0, stdout=b"", stderr=b"")
    with patch("feishu_onboard.flow.lark_config_init", return_value=p_run):
        with patch(
            "feishu_onboard.flow.lark_config_show_verify_app_id", return_value=None
        ):
            r = run_onboard(
                OnboardInput(
                    route_key="TEAM_A",
                    folder_name="My",
                    dify_target_key="X",
                    dataset_id="ds1",
                    qa_rule_file="rules/qa/a.mdc",
                ),
                env_path=envp,
                httpx_client=client,
            )
    assert r.exit_ok
    assert r.stage_b_index_written
    assert r.public_ok and r.lark_ok
    text = envp.read_text(encoding="utf-8")
    assert "FEISHU_FOLDER_ROUTE_KEYS=TEAM_A" in text.replace(" ", "")
    assert "FEISHU_FOLDER_TEAM_A_TOKEN=fld_new" in text


def test_collaborator_fails_no_stage_b(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    _rules_file(tmp_path)
    envp = tmp_path / ".env"
    _write_env(envp, _DELEGATE)

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "tenant_access_token" in u:
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t0", "expire": 60})
        if "root_folder/meta" in u:
            return httpx.Response(
                200,
                json={"code": 0, "data": {"token": "nod_root", "id": "1", "user_id": "2"}},
            )
        if "create_folder" in u:
            return httpx.Response(200, json={"code": 0, "data": {"token": "fld_p", "url": "u"}})
        if "permissions" in u and "members" in u and "public" not in u:
            return httpx.Response(200, json={"code": 1063003, "msg": "deny"})
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    p_run = MagicMock(returncode=0)
    with patch("feishu_onboard.flow.lark_config_init", return_value=p_run):
        with patch("feishu_onboard.flow.lark_config_show_verify_app_id"):
            r = run_onboard(
                OnboardInput(
                    route_key="B",
                    folder_name="F",
                    dify_target_key="X",
                    dataset_id="d",
                    qa_rule_file="rules/qa/a.mdc",
                ),
                env_path=envp,
                httpx_client=client,
            )
    assert not r.exit_ok
    assert r.partial
    assert not r.stage_b_index_written
    assert "1063003" in (r.message or "")
    t = envp.read_text()
    assert "FEISHU_FOLDER_ROUTE_KEYS" not in t


def test_lark_fails_no_stage_b(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    _rules_file(tmp_path)
    envp = tmp_path / ".env"
    _write_env(envp, _DELEGATE)

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "tenant_access_token" in u:
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t0", "expire": 60})
        if "root_folder/meta" in u:
            return httpx.Response(
                200,
                json={"code": 0, "data": {"token": "nod_root", "id": "1", "user_id": "2"}},
            )
        if "create_folder" in u:
            return httpx.Response(200, json={"code": 0, "data": {"token": "fld_l", "url": "u"}})
        if "permissions" in u and "members" in u and "public" not in u:
            return httpx.Response(200, json={"code": 0, "data": {}})
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    p_run = subprocess.CompletedProcess(
        [""], 1, stdout=b"", stderr=b"synthetic lark error line"
    )
    with patch("feishu_onboard.flow.lark_config_init", return_value=p_run):
        with patch("feishu_onboard.flow.lark_config_show_verify_app_id"):
            r = run_onboard(
                OnboardInput(
                    route_key="C",
                    folder_name="F",
                    dify_target_key="X",
                    dataset_id="d",
                    qa_rule_file="rules/qa/a.mdc",
                ),
                env_path=envp,
                httpx_client=client,
            )
    assert not r.exit_ok
    assert r.partial
    assert r.public_ok
    assert not r.lark_ok
    assert not r.stage_b_index_written
    assert "stderr" in (r.message or "")
    assert "synthetic" in (r.message or "")


def test_token_conflict_other_route(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    _rules_file(tmp_path)
    envp = tmp_path / ".env"
    _write_env(
        envp,
        _DELEGATE
        + "\n".join(
            [
                "FEISHU_FOLDER_ROUTE_KEYS=OTHER",
                "FEISHU_FOLDER_OTHER_NAME=o",
                "FEISHU_FOLDER_OTHER_TOKEN=fld_dup",
                "FEISHU_FOLDER_OTHER_DIFY_TARGET_KEY=X",
                "FEISHU_FOLDER_OTHER_DATASET_ID=d0",
                "FEISHU_FOLDER_OTHER_QA_RULE_FILE=rules/qa/a.mdc",
            ]
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "tenant_access_token" in u:
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t0", "expire": 60})
        if "root_folder/meta" in u:
            return httpx.Response(
                200,
                json={"code": 0, "data": {"token": "nod_root", "id": "1", "user_id": "2"}},
            )
        if "create_folder" in u:
            return httpx.Response(200, json={"code": 0, "data": {"token": "fld_dup", "url": "u"}})
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with patch("feishu_onboard.flow.lark_config_init", return_value=MagicMock(returncode=0)):
        with patch("feishu_onboard.flow.lark_config_show_verify_app_id"):
            r = run_onboard(
                OnboardInput(
                    route_key="NEW_R",
                    folder_name="F",
                    dify_target_key="X",
                    dataset_id="d",
                    qa_rule_file="rules/qa/a.mdc",
                ),
                env_path=envp,
                httpx_client=client,
            )
    assert not r.exit_ok
    assert "已被其他" in (r.message or "")


def test_resume_only_index_stage_b(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    _rules_file(tmp_path)
    envp = tmp_path / ".env"
    _write_env(
        envp,
        _DELEGATE
        + "\n".join(
            [
                "FEISHU_FOLDER_TEAM_D_NAME=n",
                "FEISHU_FOLDER_TEAM_D_TOKEN=fld_exist",
                "FEISHU_FOLDER_TEAM_D_DIFY_TARGET_KEY=X",
                "FEISHU_FOLDER_TEAM_D_DATASET_ID=ds1",
                "FEISHU_FOLDER_TEAM_D_QA_RULE_FILE=rules/qa/a.mdc",
            ]
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "tenant_access_token" in u:
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t0", "expire": 60})
        if "create_folder" in u:
            return httpx.Response(500, text="no create in resume only B")
        if "permissions" in u and "members" in u and "public" not in u:
            return httpx.Response(200, json={"code": 0, "data": {}})
        return httpx.Response(500, text="?" + u)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with patch("feishu_onboard.flow.lark_config_init", return_value=MagicMock(returncode=0)):
        with patch("feishu_onboard.flow.lark_config_show_verify_app_id"):
            r = run_onboard(
                OnboardInput(
                    route_key="TEAM_D",
                    folder_name="n",
                    dify_target_key="X",
                    dataset_id="ds1",
                    qa_rule_file="rules/qa/a.mdc",
                ),
                env_path=envp,
                httpx_client=client,
            )
    assert r.exit_ok
    assert r.stage_b_index_written
    t = envp.read_text(encoding="utf-8")
    assert "FEISHU_FOLDER_ROUTE_KEYS" in t
    assert "TEAM_D" in t


def test_lark_cli_not_in_path_file_not_found(tmp_path, monkeypatch) -> None:
    """Windows 上 lark-cli 未安装时 subprocess 抛 FileNotFoundError，应落到可读 message 而非 未预期错误。"""
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    _rules_file(tmp_path)
    envp = tmp_path / ".env"
    _write_env(envp, _DELEGATE)

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "tenant_access_token" in u:
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t0", "expire": 60})
        if "root_folder/meta" in u:
            return httpx.Response(
                200, json={"code": 0, "data": {"token": "r", "id": "1", "user_id": "2"}}
            )
        if "create_folder" in u:
            return httpx.Response(200, json={"code": 0, "data": {"token": "fld_lark", "url": "u"}})
        if "permissions" in u and "members" in u and "public" not in u:
            return httpx.Response(200, json={"code": 0, "data": {}})
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=30.0)
    with patch(
        "feishu_onboard.flow.lark_config_init",
        side_effect=FileNotFoundError(2, "no lark", "lark-cli"),
    ):
        r = run_onboard(
            OnboardInput(
                route_key="E",
                folder_name="f",
                dify_target_key="X",
                dataset_id="d",
                qa_rule_file="rules/qa/a.mdc",
            ),
            env_path=envp,
            httpx_client=client,
        )
    assert not r.exit_ok
    assert r.partial
    assert "lark-cli" in (r.message or "")
    assert "FEISHU_FOLDER_E_TOKEN=fld_lark" in envp.read_text(encoding="utf-8")
