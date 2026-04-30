"""One-shot: dump Redis pipeline state for one Feishu file_token / document_id."""
from __future__ import annotations

import json
import os
import sys

DOC = os.environ.get("TRACE_DOC_ID", "").strip()
if not DOC:
    print("set TRACE_DOC_ID", file=sys.stderr)
    raise SystemExit(2)
if not os.environ.get("VLA_WORKSPACE_ROOT", "").strip():
    print("VLA_WORKSPACE_ROOT required", file=sys.stderr)
    raise SystemExit(2)

from redis import Redis  # noqa: E402
from webhook_cursor_executor.settings import get_executor_settings  # noqa: E402


def main() -> int:
    r = Redis.from_url(get_executor_settings().redis_url, decode_responses=True)
    for suffix in (
        f"webhook:doc:snapshot:{DOC}",
        f"webhook:doc:version:{DOC}",
        f"webhook:doc:runlock:{DOC}",
        f"webhook:doc:rerun:{DOC}",
    ):
        v = r.get(suffix)
        print(suffix, "=>", v if v is None or len(v) < 500 else v[:500] + "...")

    runlock = r.get(f"webhook:doc:runlock:{DOC}")
    if runlock:
        rid = runlock
        for suffix in (f"webhook:run:context:{rid}", f"webhook:run:result:{rid}"):
            v = r.get(suffix)
            print(suffix, "=>", v if v is None or len(v) < 800 else v[:800] + "...")

    print("rq:queue:vla:default len", r.llen("rq:queue:vla:default"))

    # recent event_seen containing doc? expensive scan — sample keys with SCAN
    n = 0
    for key in r.scan_iter("webhook:event_seen:*", count=200):
        n += 1
    print("webhook:event_seen total keys (scan sample cap not total):", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
