from pathlib import Path
from unittest.mock import patch

from bootstrap.install_packages import install_all


def test_install_all_invokes_pip(tmp_path):
    clone = tmp_path / "c"
    for name in ("vla_env_contract", "webhook", "onboard", "dify_upload", "feishu_fetch"):
        p = clone / name
        p.mkdir(parents=True)
        (p / "pyproject.toml").write_text("[project]\nname=dummy\nversion=0\n", encoding="utf-8")
    recorded: list[tuple[list[str], str | None]] = []

    def fake_run(args: list[str], *, cwd: str | None = None) -> None:
        recorded.append((args, cwd))

    with patch("bootstrap.install_packages._pip_run", fake_run):
        install_all(clone)
    edit_cwd = {
        Path(c).resolve()
        for args, c in recorded
        if args == ["install", "-e", "."] and c is not None
    }
    assert edit_cwd == {
        (clone / n).resolve()
        for n in ("vla_env_contract", "webhook", "onboard", "dify_upload", "feishu_fetch")
    }
    assert any(args == ["install", "markitdown"] and cwd is None for args, cwd in recorded)
