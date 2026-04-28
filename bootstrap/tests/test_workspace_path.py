import pytest
from pathlib import Path

from bootstrap.workspace_path import validate_workspace_root_path


def test_rejects_non_ascii_segment():
    p = Path(r"C:\example\ascii-workspace-root")
    validate_workspace_root_path(p)

    bad = Path(r"C:\example\工作区\bad")
    with pytest.raises(ValueError, match="ASCII"):
        validate_workspace_root_path(bad)


def test_rejects_space_in_segment():
    bad = Path(r"C:\example\new vla\workspace")
    with pytest.raises(ValueError):
        validate_workspace_root_path(bad)


def test_rejects_nested_workspace_under_clone():
    clone = Path(r"C:\example\repo")
    ws = Path(r"C:\example\repo\sub\workspace")
    with pytest.raises(ValueError, match="nested"):
        validate_workspace_root_path(ws, clone_root=clone)
