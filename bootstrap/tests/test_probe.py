from pathlib import Path
from unittest.mock import MagicMock, patch

from bootstrap.probe import run_probe


def test_probe_no_http_returns_zero_after_doctor_skipped(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("REDIS_URL=\n", encoding="utf-8")
    with patch("bootstrap.probe.run_doctor", return_value=0):
        code = run_probe(
            clone_root=tmp_path / "clone",
            workspace=ws,
            no_http=True,
            skip_doctor=True,
        )
    assert code == 0


def test_probe_no_http_runs_doctor_when_not_skipped(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("REDIS_URL=\n", encoding="utf-8")
    with patch("bootstrap.probe.run_doctor", return_value=0) as doc:
        run_probe(
            clone_root=tmp_path / "c",
            workspace=ws,
            no_http=True,
            skip_doctor=False,
        )
    assert doc.called


def test_probe_http_fails_when_base_missing(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("FOO=bar\n", encoding="utf-8")
    code = run_probe(
        clone_root=tmp_path / "c",
        workspace=ws,
        no_http=False,
        webhook_http_base=None,
        skip_doctor=True,
    )
    assert code == 1


def test_probe_http_success_via_cli_base(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("FOO=bar\n", encoding="utf-8")

    inner = MagicMock()
    inner.getcode.return_value = 200
    inner.read.return_value = b"{}"
    cm = MagicMock()
    cm.__enter__.return_value = inner
    cm.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=cm) as uo:
        code = run_probe(
            clone_root=tmp_path / "c",
            workspace=ws,
            no_http=False,
            webhook_http_base="http://127.0.0.1:9",
            skip_doctor=True,
        )

    assert code == 0
    assert uo.call_args[0][0] == "http://127.0.0.1:9/health"


def test_probe_http_open_failure_returns_one(tmp_path, capsys):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("WEBHOOK_PROBE_BASE=http://127.0.0.1:1\n", encoding="utf-8")

    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        code = run_probe(
            clone_root=tmp_path / "c",
            workspace=ws,
            no_http=False,
            skip_doctor=True,
        )
    assert code == 1
    assert "ERROR" in capsys.readouterr().err


def test_probe_propagates_doctor_nonzero(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("X=1\n", encoding="utf-8")
    with patch("bootstrap.probe.run_doctor", return_value=1):
        code = run_probe(
            clone_root=tmp_path / "c",
            workspace=ws,
            no_http=True,
            skip_doctor=False,
        )
    assert code == 1
