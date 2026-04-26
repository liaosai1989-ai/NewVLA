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

from feishu_fetch import FeishuFetchError, FeishuFetchRequest, fetch_feishu_content


class FakeCompletedProcess:
    def __init__(self, *, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _mock_cli_path(args):
    return Path(args[0]).name.lower() in {"lark-cli", "lark-cli.cmd", "lark-cli.exe"}


def test_cloud_docx_fetches_xml_and_writes_artifact(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if len(args) == 2 and _mock_cli_path(args) and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if _mock_cli_path(args) and args[1:3] == ["docs", "+fetch"]:
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

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "lark-cli" else None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            document_id="doccnxxxx",
            output_dir=tmp_path,
            title_hint="Weekly Sync",
        )
    )

    artifact = Path(result.artifact_path)
    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8") == "<doc><p>Hello</p></doc>"
    assert result.ingest_kind == "cloud_docx"
    assert result.title == "Weekly Sync"
    assert calls[1][1:] == [
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
        "--scope",
        "docx",
        "--document-id",
        "doccnxxxx",
    ]


def test_cloud_docx_wraps_missing_lark_cli(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("lark-cli")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="cloud_docx",
                document_id="doccnxxxx",
                output_dir=tmp_path,
            )
        )

    assert exc.value.code == "dependency_error"
    assert "找不到 lark-cli" in str(exc.value)


def test_cloud_docx_rejects_empty_content(monkeypatch, tmp_path):
    def fake_run(args, **kwargs):
        if len(args) == 2 and _mock_cli_path(args) and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        return FakeCompletedProcess(
            stdout=json.dumps({"data": {"document": {"title": "Empty", "content": ""}}})
        )

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "lark-cli" else None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="cloud_docx",
                document_id="doccnxxxx",
                output_dir=tmp_path,
            )
        )

    assert exc.value.code == "empty_content"
    assert "正文为空" in str(exc.value)


def test_drive_file_keeps_direct_readable_file_without_markitdown(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if len(args) == 2 and _mock_cli_path(args) and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if _mock_cli_path(args) and args[1:3] == ["drive", "+download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "notes.md").write_text("# done\n", encoding="utf-8")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    def fail_import(name):
        if name == "markitdown":
            raise AssertionError("markitdown should not be imported for .md")
        return importlib.import_module(name)

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "lark-cli" else None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(importlib, "import_module", fail_import)

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="drive_file",
            file_token="filecnxxxx",
            doc_type="file",
            output_dir=tmp_path,
        )
    )

    artifact = Path(result.artifact_path)
    assert artifact.name == "notes.md"
    assert artifact.suffix == ".md"
    assert artifact.read_text(encoding="utf-8") == "# done\n"
    assert result.ingest_kind == "drive_file"
    assert calls[1][1:3] == ["drive", "+download"]


def test_drive_file_exports_docx_with_explicit_format_and_converts_to_markdown(
    tmp_path, monkeypatch
):
    calls = []

    class FakeMarkItDown:
        def convert(self, source):
            assert Path(source).suffix == ".docx"
            return type("Result", (), {"text_content": "# converted\n\nhello"})()

    def fake_run(args, **kwargs):
        calls.append(args)
        if len(args) == 2 and _mock_cli_path(args) and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if _mock_cli_path(args) and args[1:3] == ["drive", "+export"]:
            return FakeCompletedProcess(stdout=json.dumps({"data": {"task_id": "task_1"}}))
        if _mock_cli_path(args) and args[1:3] == ["drive", "+task_result"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"data": {"file_token": "exported_1"}})
            )
        if _mock_cli_path(args) and args[1:3] == ["drive", "+export-download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "weekly.docx").write_bytes(b"docx-bytes")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "lark-cli" else None)
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
        )
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
    ] == calls[1][1:7]
    assert calls[2][1:5] == ["drive", "+task_result", "--scenario", "export"]
    assert calls[3][1:3] == ["drive", "+export-download"]


def test_drive_file_requires_markitdown_only_for_convertible_suffix(
    tmp_path, monkeypatch
):
    def fake_run(args, **kwargs):
        if len(args) == 2 and _mock_cli_path(args) and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if _mock_cli_path(args) and args[1:3] == ["drive", "+export"]:
            return FakeCompletedProcess(
                stdout=json.dumps({"data": {"file_token": "exported_1"}})
            )
        if _mock_cli_path(args) and args[1:3] == ["drive", "+export-download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "weekly.docx").write_bytes(b"docx-bytes")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "lark-cli" else None)
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
            )
        )

    assert exc.value.code == "dependency_error"
    assert "找不到 MarkItDown" in str(exc.value)


def test_drive_file_rejects_unsupported_suffix_and_runtime_failures(
    tmp_path, monkeypatch
):
    call_count = {"value": 0}

    def fake_run(args, **kwargs):
        call_count["value"] += 1
        if len(args) == 2 and _mock_cli_path(args) and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if call_count["value"] == 2:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "binary.exe").write_bytes(b"boom")
            return FakeCompletedProcess(stdout="downloaded")
        return FakeCompletedProcess(returncode=2, stderr="permission denied")

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "lark-cli" else None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as unsupported:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="file",
                output_dir=tmp_path,
            )
        )
    assert unsupported.value.code == "request_error"
    assert "当前文件格式不在第一版支持范围内" in str(unsupported.value)

    with pytest.raises(FeishuFetchError) as runtime_failed:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="file",
                output_dir=tmp_path / "runtime",
            )
        )
    assert runtime_failed.value.code == "runtime_error"
    assert "lark-cli 执行失败" in str(runtime_failed.value)


def test_drive_file_rejects_ambiguous_new_files_after_download(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        if len(args) == 2 and _mock_cli_path(args) and args[1] == "--help":
            return FakeCompletedProcess(stdout="usage")
        if _mock_cli_path(args) and args[1:3] == ["drive", "+download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "notes.md").write_text("# done\n", encoding="utf-8")
            (out_dir / "fetch-log.json").write_text('{"ok":true}\n', encoding="utf-8")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    monkeypatch.setattr(shutil, "which", lambda name: name if name == "lark-cli" else None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="file",
                output_dir=tmp_path,
            )
        )

    assert exc.value.code == "runtime_error"
    assert "多个新文件" in str(exc.value)


def test_cloud_docx_runs_against_local_mock_lark_cli(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "mock_lark_cli.py"
    assert fixture.exists()

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
        )
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
    assert log_entries[1]["args"] == [
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
        "--scope",
        "docx",
        "--document-id",
        "doccn_local_mock",
    ]
