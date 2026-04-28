import os
import sys
from pathlib import Path

import pytest

from bootstrap import junction


@pytest.mark.skipif(sys.platform != "win32", reason="junctions are Windows P0")
def test_ensure_junction_creates_link(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "x.txt").write_text("hi", encoding="utf-8")
    link = tmp_path / "link"
    junction.ensure_junction(link, target)
    assert link.is_dir()
    assert (link / "x.txt").read_text(encoding="utf-8") == "hi"
