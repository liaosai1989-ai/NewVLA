from __future__ import annotations

import string
from pathlib import Path

_ALLOWED_EXTRA = frozenset("-_")


def _segment_ok(name: str) -> bool:
    if not name:
        return False
    return all(
        (c in string.ascii_letters or c.isdigit() or c in _ALLOWED_EXTRA) for c in name
    )


def validate_workspace_root_path(path: Path, *, clone_root: Path | None = None) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        raise ValueError("workspace root must be absolute path")
    resolved = expanded.resolve()
    for seg in resolved.parts:
        if not seg or seg in ("/", "\\"):
            continue
        # Windows: anchor segment like 'C:\\' has ':' at position 1
        if len(seg) >= 2 and seg[1] == ":":
            continue
        if not _segment_ok(seg):
            raise ValueError(
                "workspace path segment must be ASCII letters/digits/hyphen/underscore only: "
                f"{seg!r}"
            )
    if clone_root is not None:
        cr = clone_root.resolve()
        wr = resolved
        if wr.is_relative_to(cr):
            raise ValueError("workspace root must not be nested under clone root")
        if cr.is_relative_to(wr):
            raise ValueError("clone root must not be nested under workspace root")
    return resolved
