from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

_ENV_FILE_ENCODING = "utf-8-sig"  # 与记事本「UTF-8 带签名」首行键名错位、以及 BOM 对 id/secret 的干扰


def _norm_env_value(raw: str) -> str:
    v = raw.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[0] == v[-1]:
        v = v[1:-1].strip()
    return v


def load_flat_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding=_ENV_FILE_ENCODING).splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        out[k] = _norm_env_value(v)
    return out


def set_keys_atomic(path: Path, updates: dict[str, str], *, create_backup: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if create_backup and path.is_file():
        path.with_suffix(path.suffix + ".bak").write_bytes(path.read_bytes())

    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding=_ENV_FILE_ENCODING).splitlines(keepends=True)

    def norm_line(line: str) -> tuple[str | None, str | None]:
        raw = line
        t = line.lstrip()
        if not t or t.lstrip().startswith("#"):
            return None, raw
        if "=" not in t:
            return None, raw
        k, _v = t.split("=", 1)
        return k.strip(), raw

    for k, v in updates.items():
        new_line = f"{k}={v}\n"
        idxs: list[int] = []
        for i, line in enumerate(lines):
            k2, _ = norm_line(line)
            if k2 == k:
                idxs.append(i)
        if idxs:
            first = idxs[0]
            lines[first] = new_line
            for i in reversed(idxs[1:]):
                del lines[i]
        else:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(new_line)

    dir_ = path.parent
    fd, tmp = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=dir_)
    try:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines if lines else [""])
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
