from pathlib import Path

import pytest

from bootstrap import paths


def test_default_clone_root_is_repo_root():
    cr = paths.default_clone_root()
    assert (cr / "webhook" / "pyproject.toml").is_file()
    assert (cr / "bootstrap" / "pyproject.toml").is_file()


def test_assert_clone_root_rejects_random_directory(tmp_path):
    with pytest.raises(ValueError, match="clone root"):
        paths.assert_clone_root_looks_sane(tmp_path)
