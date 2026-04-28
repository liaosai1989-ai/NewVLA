from pathlib import Path
from unittest.mock import patch

from bootstrap.install_packages import install_all


def test_install_all_invokes_pip(tmp_path):
    clone = tmp_path / "c"
    for name in ("webhook", "onboard", "dify_upload", "feishu_fetch"):
        p = clone / name
        p.mkdir(parents=True)
        (p / "pyproject.toml").write_text("[project]\nname=dummy\nversion=0\n", encoding="utf-8")
    recorded: list[list[str]] = []

    def fake_run(args: list[str]) -> None:
        recorded.append(args)

    with patch("bootstrap.install_packages._pip_run", fake_run):
        install_all(clone)
    blob = "\n".join(" ".join(args) for args in recorded)
    assert "webhook" in blob
    assert "markitdown" in blob
