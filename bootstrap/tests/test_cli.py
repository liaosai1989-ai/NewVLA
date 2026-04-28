import subprocess
import sys
from pathlib import Path


def test_bootstrap_module_invokable():
    cli = Path(__file__).resolve().parents[1] / "src" / "bootstrap" / "cli.py"
    r = subprocess.run([sys.executable, str(cli), "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "doctor" in r.stdout


def test_bootstrap_help_lists_interactive_setup():
    cli = Path(__file__).resolve().parents[1] / "src" / "bootstrap" / "cli.py"
    r = subprocess.run([sys.executable, str(cli), "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "interactive-setup" in r.stdout
