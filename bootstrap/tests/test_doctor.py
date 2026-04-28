import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bootstrap.doctor import run_doctor


@pytest.fixture
def py312(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 12, 0, "final", 0))


def _stub_embedded_workspace_layout(ws: Path) -> None:
    (ws / "runtime" / "webhook").mkdir(parents=True)
    (ws / "runtime" / "webhook" / "pyproject.toml").write_text("[project]\nname=w\n", encoding="utf-8")
    (ws / "tools" / "dify_upload").mkdir(parents=True)
    (ws / "tools" / "dify_upload" / "pyproject.toml").write_text("[project]\nname=d\n", encoding="utf-8")
    (ws / "tools" / "feishu_fetch").mkdir(parents=True)
    (ws / "tools" / "feishu_fetch" / "pyproject.toml").write_text("[project]\nname=f\n", encoding="utf-8")
    (ws / "vla_env_contract").mkdir(parents=True)
    (ws / "vla_env_contract" / "pyproject.toml").write_text("[project]\nname=v\n", encoding="utf-8")


def test_doctor_fails_without_markitdown(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("K=v\n", encoding="utf-8")
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\cursor"):
        with patch("bootstrap.doctor._import_markitdown", side_effect=ImportError("no")):
            code = run_doctor(clone_root=clone, workspace=ws)
    assert code != 0


def test_doctor_ok_minimal_mocks(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _stub_embedded_workspace_layout(ws)
    (ws / ".env").write_text("K=v\n", encoding="utf-8")
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                with patch("bootstrap.doctor._workspace_import_paths_ok", return_value=True):
                    with patch("bootstrap.doctor.redis.from_url") as fr:
                        fr.return_value.ping.return_value = True
                        code = run_doctor(clone_root=clone, workspace=ws)
    assert code == 0


def test_doctor_fails_incomplete_env_route_groups(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _stub_embedded_workspace_layout(ws)
    (ws / ".env").write_text(
        "FEISHU_FOLDER_ROUTE_KEYS=MAIN\nFEISHU_FOLDER_MAIN_NAME=x\n",
        encoding="utf-8",
    )
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                with patch("bootstrap.doctor._workspace_import_paths_ok", return_value=True):
                    code = run_doctor(clone_root=clone, workspace=ws)
    assert code != 0


def test_doctor_ok_full_env_route_groups(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _stub_embedded_workspace_layout(ws)
    (ws / ".env").write_text(
        "\n".join(
            [
                "FEISHU_FOLDER_ROUTE_KEYS=MAIN",
                "FEISHU_FOLDER_MAIN_NAME=main",
                "FEISHU_FOLDER_MAIN_TOKEN=tok",
                "FEISHU_FOLDER_MAIN_DIFY_TARGET_KEY=DEFAULT",
                "FEISHU_FOLDER_MAIN_DATASET_ID=ds",
                "FEISHU_FOLDER_MAIN_QA_RULE_FILE=rules/q.md",
                "K=v",
                "",
            ]
        ),
        encoding="utf-8",
    )
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                with patch("bootstrap.doctor._workspace_import_paths_ok", return_value=True):
                    code = run_doctor(clone_root=clone, workspace=ws)
    assert code == 0


def test_doctor_fails_onboard_directory_present(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _stub_embedded_workspace_layout(ws)
    (ws / "onboard").mkdir()
    (ws / ".env").write_text("K=v\n", encoding="utf-8")
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                with patch("bootstrap.doctor._workspace_import_paths_ok", return_value=True):
                    code = run_doctor(clone_root=clone, workspace=ws)
    assert code != 0


def test_doctor_fails_when_import_paths_not_under_workspace(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _stub_embedded_workspace_layout(ws)
    (ws / ".env").write_text("K=v\n", encoding="utf-8")
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                with patch("bootstrap.doctor._workspace_import_paths_ok", return_value=False):
                    code = run_doctor(clone_root=clone, workspace=ws)
    assert code != 0


def test_doctor_fails_when_tool_path_resolves_under_clone(py312, tmp_path, monkeypatch):
    clone = tmp_path / "clone"
    clone.mkdir()
    fake_du = clone / "dify_upload"
    fake_du.mkdir()
    ws = tmp_path / "ws"
    ws.mkdir()
    _stub_embedded_workspace_layout(ws)
    (ws / ".env").write_text("K=v\n", encoding="utf-8")

    real = Path.resolve

    def fake_resolve(self, *a, **kw):
        if self.name == "dify_upload" and "tools" in self.parts:
            return real(fake_du, *a, **kw)
        return real(self, *a, **kw)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                with patch("bootstrap.doctor._workspace_import_paths_ok", return_value=True):
                    code = run_doctor(clone_root=clone, workspace=ws)
    assert code != 0
