import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bootstrap.doctor import run_doctor


@pytest.fixture
def py312(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 12, 0, "final", 0))


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
    (ws / ".env").write_text("K=v\n", encoding="utf-8")
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                with patch("bootstrap.doctor.redis.from_url") as fr:
                    fr.return_value.ping.return_value = True
                    code = run_doctor(clone_root=clone, workspace=ws)
    assert code == 0


def test_doctor_fails_incomplete_env_route_groups(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text(
        "FEISHU_FOLDER_ROUTE_KEYS=MAIN\nFEISHU_FOLDER_MAIN_NAME=x\n",
        encoding="utf-8",
    )
    clone = tmp_path / "clone"
    clone.mkdir()
    with patch("bootstrap.doctor.shutil.which", return_value=r"C:\fake\bin"):
        with patch("bootstrap.doctor._import_markitdown", return_value=MagicMock()):
            with patch("bootstrap.doctor._import_pipeline_packages"):
                code = run_doctor(clone_root=clone, workspace=ws)
    assert code != 0


def test_doctor_ok_full_env_route_groups(py312, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
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
                code = run_doctor(clone_root=clone, workspace=ws)
    assert code == 0
