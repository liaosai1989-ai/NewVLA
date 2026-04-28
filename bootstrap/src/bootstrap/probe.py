from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

from bootstrap.doctor import run_doctor
from bootstrap.env_dotenv import read_env_keys

_HTTP_TIMEOUT_SEC = 5.0


def run_probe(
    *,
    clone_root: Path,
    workspace: Path,
    no_http: bool,
    webhook_http_base: str | None = None,
    skip_doctor: bool = False,
) -> int:
    if not skip_doctor:
        doctor_code = run_doctor(clone_root=clone_root, workspace=workspace)
        if doctor_code != 0:
            return doctor_code

    ws_env = workspace / ".env"
    keys = read_env_keys(ws_env)
    probe_key = "WEBHOOK_PROBE_BASE"
    env_base = (keys.get(probe_key) or "").strip()

    if no_http:
        print(
            "WARNING: RQ/worker reachability not checked by probe (optional).",
            file=sys.stderr,
        )
        return 0

    effective = (webhook_http_base or "").strip() if webhook_http_base is not None else env_base
    if not effective:
        print(
            f"ERROR: {probe_key} empty and no --webhook-http-base; HTTP health check skipped unsuccessfully.",
            file=sys.stderr,
        )
        return 1

    base = effective.rstrip("/")
    url = f"{base}/health"
    try:
        with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT_SEC) as resp:  # noqa: S310
            code = resp.getcode()
            if code != 200:
                print(
                    f"ERROR: HTTP GET {url!r} expected status 200, got {code}",
                    file=sys.stderr,
                )
                return 1
            _ = resp.read()
    except OSError as e:
        print(f"ERROR: HTTP GET {url!r} failed: {e}", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP GET {url!r} failed: HTTP {e.code}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"ERROR: HTTP GET {url!r} failed: {e}", file=sys.stderr)
        return 1

    return 0
