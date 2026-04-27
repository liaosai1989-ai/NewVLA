import importlib
import json
import os
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

from conftest import write_root_dotenv
from feishu_fetch import FeishuFetchError, FeishuFetchRequest, fetch_feishu_content


class FakeCompletedProcess:
    def __init__(self, *, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _which_lark(name: str | None) -> str | None:
    if not name:
        return None
    base = Path(name).name.lower()
    if base in {"lark-cli", "lark-cli.cmd", "lark-cli.exe"}:
        return name
    return None


def test_cloud_docx_fetches_xml_and_writes_artifact(tmp_path, monkeypatch):
    app_id = "cli_test"
    env_file = write_root_dotenv(tmp_path, feishu_app_id=app_id)
    calls = []

    def fake_run(args, **kwargs):
        calls.append((list(args), dict(kwargs)))
        assert kwargs.get("cwd") == tmp_path.resolve()
        if len(args) >= 2 and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if len(args) >= 3 and list(args[1:3]) == ["config", "show"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"appId": app_id}, ensure_ascii=False)
            )
        if len(args) >= 3 and args[1:3] == ["docs", "+fetch"]:
            payload = {
                "data": {
                    "document": {
                        "title": "Weekly Sync",
                        "content": "<doc><p>Hello</p></doc>",
                    }
                }
            }
            return FakeCompletedProcess(stdout=json.dumps(payload, ensure_ascii=False))
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", _which_lark)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            document_id="doccnxxxx",
            output_dir=tmp_path,
            title_hint="Weekly Sync",
        ),
        env_file=env_file,
    )

    artifact = Path(result.artifact_path)
    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8") == "<doc><p>Hello</p></doc>"
    assert result.ingest_kind == "cloud_docx"
    assert result.title == "Weekly Sync"
    assert calls[2][0][1:] == [
        "docs",
        "+fetch",
        "--api-version",
        "v2",
        "--format",
        "json",
        "--doc-format",
        "xml",
        "--detail",
        "simple",
        "--doc",
        "doccnxxxx",
    ]


def test_cloud_docx_wraps_missing_lark_cli(monkeypatch, tmp_path):
    write_root_dotenv(tmp_path)

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("lark-cli")

    monkeypatch.setattr(shutil, "which", lambda _n: None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="cloud_docx",
                document_id="doccnxxxx",
                output_dir=tmp_path,
            ),
            env_file=tmp_path / ".env",
        )

    assert exc.value.code == "dependency_error"
    assert "PATH 上找不到命令" in str(exc.value)


def test_cloud_docx_maps_stderr_permission_to_permission_error(monkeypatch, tmp_path):
    app_id = "cli_p1"
    write_root_dotenv(tmp_path, feishu_app_id=app_id)

    def fake_run(args, **kwargs):
        assert kwargs.get("cwd") == tmp_path.resolve()
        if len(args) >= 2 and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if len(args) >= 3 and list(args[1:3]) == ["config", "show"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"appId": app_id}, ensure_ascii=False)
            )
        if len(args) >= 3 and args[1:3] == ["docs", "+fetch"]:
            return FakeCompletedProcess(
                returncode=2, stderr="403 forbidden: no permission to access this document"
            )
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", _which_lark)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="cloud_docx",
                document_id="doccnxxxx",
                output_dir=tmp_path,
            ),
            env_file=tmp_path / ".env",
        )
    assert exc.value.code == "permission_error"


def test_cloud_docx_rejects_empty_content(monkeypatch, tmp_path):
    app_id = "cli_empty"
    write_root_dotenv(tmp_path, feishu_app_id=app_id)

    def fake_run(args, **kwargs):
        assert kwargs.get("cwd") == tmp_path.resolve()
        if len(args) >= 2 and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if len(args) >= 3 and list(args[1:3]) == ["config", "show"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"appId": app_id}, ensure_ascii=False)
            )
        return FakeCompletedProcess(
            stdout=json.dumps({"data": {"document": {"title": "Empty", "content": ""}}})
        )

    monkeypatch.setattr(shutil, "which", _which_lark)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="cloud_docx",
                document_id="doccnxxxx",
                output_dir=tmp_path,
            ),
            env_file=tmp_path / ".env",
        )

    assert exc.value.code == "empty_content"
    assert "正文为空" in str(exc.value)


def test_drive_file_keeps_direct_readable_file_without_markitdown(tmp_path, monkeypatch):
    app_id = "cli_df1"
    write_root_dotenv(tmp_path, feishu_app_id=app_id)
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        assert kwargs.get("cwd") == tmp_path.resolve()
        if len(args) >= 2 and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if len(args) >= 3 and list(args[1:3]) == ["config", "show"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"appId": app_id}, ensure_ascii=False)
            )
        if len(args) >= 3 and args[1:3] == ["drive", "+download"]:
            out_rel = args[args.index("--output") + 1]
            out_path = (tmp_path / out_rel).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("# done\n", encoding="utf-8")
            return FakeCompletedProcess(
                stdout=json.dumps(
                    {"ok": True, "data": {"saved_path": str(out_path)}},
                    ensure_ascii=False,
                )
            )
        raise AssertionError(args)

    def fail_import(name):
        if name == "markitdown":
            raise AssertionError("markitdown should not be imported for .md")
        return importlib.import_module(name)

    monkeypatch.setattr(shutil, "which", _which_lark)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(importlib, "import_module", fail_import)

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="drive_file",
            file_token="filecnxxxx",
            doc_type="file",
            output_dir=tmp_path,
        ),
        env_file=tmp_path / ".env",
    )

    artifact = Path(result.artifact_path)
    assert artifact.name == "_filecnxxxx_download.md"
    assert artifact.suffix == ".md"
    assert artifact.read_text(encoding="utf-8") == "# done\n"
    assert result.ingest_kind == "drive_file"
    assert calls[2][1:3] == ["drive", "+download"]
    assert "--output" in calls[2]
    assert "--overwrite" in calls[2]


def test_drive_file_exports_docx_with_explicit_format_and_converts_to_markdown(
    tmp_path, monkeypatch
):
    app_id = "cli_df2"
    write_root_dotenv(tmp_path, feishu_app_id=app_id)
    calls = []

    class FakeMarkItDown:
        def convert(self, source):
            assert Path(source).suffix == ".docx"
            return type("Result", (), {"text_content": "# converted\n\nhello"})()

    def fake_run(args, **kwargs):
        calls.append(args)
        assert kwargs.get("cwd") == tmp_path.resolve()
        if len(args) >= 2 and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if len(args) >= 3 and list(args[1:3]) == ["config", "show"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"appId": app_id}, ensure_ascii=False)
            )
        if len(args) >= 3 and args[1:3] == ["drive", "+export"]:
            return FakeCompletedProcess(stdout=json.dumps({"data": {"task_id": "task_1"}}))
        if len(args) >= 3 and args[1:3] == ["drive", "+task_result"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"data": {"file_token": "exported_1"}})
            )
        if len(args) >= 3 and args[1:3] == ["drive", "+export-download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "weekly.docx").write_bytes(b"docx-bytes")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", _which_lark)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: types.SimpleNamespace(MarkItDown=FakeMarkItDown)
        if name == "markitdown"
        else importlib.import_module(name),
    )

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="drive_file",
            file_token="filecnxxxx",
            doc_type="docx",
            output_dir=tmp_path,
            title_hint="Weekly Sync",
            timeout_seconds=5.0,
        ),
        env_file=tmp_path / ".env",
    )

    artifact = Path(result.artifact_path)
    assert artifact.suffix == ".md"
    assert artifact.read_text(encoding="utf-8") == "# converted\n\nhello"
    assert [
        "drive",
        "+export",
        "--file-token",
        "filecnxxxx",
        "--export-format",
        "docx",
    ] == calls[2][1:7]
    assert calls[3][1:5] == ["drive", "+task_result", "--scenario", "export"]
    assert calls[4][1:3] == ["drive", "+export-download"]


def test_drive_file_requires_markitdown_only_for_convertible_suffix(
    tmp_path, monkeypatch
):
    app_id = "cli_df3"
    write_root_dotenv(tmp_path, feishu_app_id=app_id)

    def fake_run(args, **kwargs):
        assert kwargs.get("cwd") == tmp_path.resolve()
        if len(args) >= 2 and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if len(args) >= 3 and list(args[1:3]) == ["config", "show"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"appId": app_id}, ensure_ascii=False)
            )
        if len(args) >= 3 and args[1:3] == ["drive", "+export"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"data": {"file_token": "exported_1"}})
            )
        if len(args) >= 3 and args[1:3] == ["drive", "+export-download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "weekly.docx").write_bytes(b"docx-bytes")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", _which_lark)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError("markitdown"))
        if name == "markitdown"
        else importlib.import_module(name),
    )

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="doc",
                output_dir=tmp_path,
            ),
            env_file=tmp_path / ".env",
        )

    assert exc.value.code == "dependency_error"
    assert "找不到 MarkItDown" in str(exc.value)


def test_drive_file_rejects_unsupported_suffix_and_runtime_failures(
    tmp_path, monkeypatch
):
    app_id = "cli_df4"
    write_root_dotenv(tmp_path, feishu_app_id=app_id)
    call_count = {"value": 0}
    first_drive_download = {"done": False}

    def fake_run(args, **kwargs):
        call_count["value"] += 1
        assert kwargs.get("cwd") == tmp_path.resolve()
        if len(args) >= 2 and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if len(args) >= 3 and list(args[1:3]) == ["config", "show"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"appId": app_id}, ensure_ascii=False)
            )
        if len(args) >= 3 and args[1:3] == ["drive", "+download"]:
            if not first_drive_download["done"]:
                first_drive_download["done"] = True
                out_rel = args[args.index("--output") + 1]
                out_path = (tmp_path / out_rel).resolve()
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"MZ boom")
                return FakeCompletedProcess(
                    stdout=json.dumps(
                        {"ok": True, "data": {"saved_path": str(out_path)}},
                        ensure_ascii=False,
                    )
                )
            return FakeCompletedProcess(returncode=2, stderr="permission denied")
        return FakeCompletedProcess(returncode=2, stderr="permission denied")

    monkeypatch.setattr(shutil, "which", _which_lark)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as unsupported:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="file",
                output_dir=tmp_path,
            ),
            env_file=tmp_path / ".env",
        )
    assert unsupported.value.code == "request_error"
    assert "当前文件格式不在第一版支持范围内" in str(unsupported.value)

    with pytest.raises(FeishuFetchError) as perm_failed:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="file",
                output_dir=tmp_path / "runtime",
            ),
            env_file=tmp_path / ".env",
        )
    assert perm_failed.value.code == "permission_error"
    assert "无权限" in str(perm_failed.value) or "权限" in str(perm_failed.value)


def test_cloud_docx_runs_against_local_mock_lark_cli(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "mock_lark_cli.py"
    assert fixture.exists()
    app_id = "cli_mock_fixture"
    root = tmp_path
    write_root_dotenv(root, feishu_app_id=app_id)
    monkeypatch.setenv("MOCK_LARK_CONFIG_APP_ID", app_id)

    shim_dir = tmp_path / "bin"
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim = shim_dir / "lark-cli.cmd"
    shim.write_text(
        f'@echo off\r\n"{sys.executable}" "{fixture}" %*\r\n',
        encoding="utf-8",
    )

    log_file = tmp_path / "mock-lark-log.jsonl"
    monkeypatch.setenv("PATH", f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("MOCK_LARK_LOG", str(log_file))

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            document_id="doccn_local_mock",
            output_dir=tmp_path / "outputs",
            title_hint="Local Mock",
        ),
        env_file=root / ".env",
    )

    artifact = Path(result.artifact_path)
    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8") == "<doc><p>Local Mock</p></doc>"
    assert result.title == "Local Mock"

    log_entries = [
        json.loads(line)
        for line in log_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert log_entries[0]["args"] == ["--help"]
    assert log_entries[1]["args"] == ["config", "show"]
    assert log_entries[2]["args"] == [
        "docs",
        "+fetch",
        "--api-version",
        "v2",
        "--format",
        "json",
        "--doc-format",
        "xml",
        "--detail",
        "simple",
        "--doc",
        "doccn_local_mock",
    ]
