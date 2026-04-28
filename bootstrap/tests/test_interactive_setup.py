from pathlib import Path
from unittest.mock import patch

from bootstrap.interactive_setup import run_interactive_setup


def test_interactive_setup_calls_pipeline_in_order(tmp_path, monkeypatch):
    clone = tmp_path / "repo"
    (clone / "webhook").mkdir(parents=True)
    (clone / "webhook" / "pyproject.toml").write_text("[project]\nname=w\nversion=0\n", encoding="utf-8")
    (clone / "bootstrap").mkdir(parents=True)
    (clone / "bootstrap" / "pyproject.toml").write_text("[project]\nname=b\nversion=0\n", encoding="utf-8")
    ws = tmp_path / "workspace_ok"
    monkeypatch.chdir(clone)

    seq = iter([str(ws)])

    def fake_input(prompt: str = "") -> str:
        try:
            return next(seq)
        except StopIteration:
            return ""

    order: list[str] = []

    def fake_install(_cr: Path) -> None:
        order.append("install")

    def fake_mat(**_kwargs: object) -> None:
        order.append("materialize")

    def fake_doctor(**kwargs):
        order.append("doctor")
        return 0

    with patch("bootstrap.interactive_setup.install_all", fake_install):
        with patch("bootstrap.interactive_setup.materialize_workspace", fake_mat):
            with patch("bootstrap.interactive_setup.run_doctor", fake_doctor):
                code = run_interactive_setup(
                    dry_run=False,
                    yes=True,
                    input_fn=fake_input,
                    print_fn=lambda *a, **k: None,
                )
    assert code == 0
    assert order == ["install", "materialize", "doctor"]
