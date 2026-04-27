from feishu_onboard.env_paths import root_dotenv_path


def test_repo_root_env_override(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_ONBOARD_REPO_ROOT", str(tmp_path))
    assert root_dotenv_path() == tmp_path / ".env"
