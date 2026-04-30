"""One-shot: recover running-without-result + drop orphan runlocks. Internal use."""
from __future__ import annotations

import json
import os
import sys

# noqa: script run with PYTHONPATH=src


def main() -> int:
    if not os.environ.get("VLA_WORKSPACE_ROOT", "").strip():
        print("VLA_WORKSPACE_ROOT required", file=sys.stderr)
        return 2
    from webhook_cursor_executor.scheduler import recover_stale_launch
    from webhook_cursor_executor.worker import build_worker_runtime

    _, store, queue = build_worker_runtime()
    r = store.redis
    recovered: list[str] = []
    for key in r.scan_iter("webhook:run:context:*", count=500):
        key_s = key if isinstance(key, str) else key.decode()
        raw = r.get(key_s)
        if not raw:
            continue
        try:
            o = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if o.get("status") != "running":
            continue
        rid = o.get("run_id") or key_s.split(":")[-1]
        if r.get(f"webhook:run:result:{rid}"):
            continue
        if recover_stale_launch(
            run_id=rid,
            state_store=store,
            queue=queue,
            summary="recovered_stale_launch:env_cleanup",
        ):
            recovered.append(rid)
            print("recovered", rid)
    orphan_del: list[tuple[str, str]] = []
    for key in r.scan_iter("webhook:doc:runlock:*", count=500):
        key_s = key if isinstance(key, str) else key.decode()
        rid = r.get(key_s)
        if not rid:
            continue
        has_ctx = r.get(f"webhook:run:context:{rid}")
        has_res = r.get(f"webhook:run:result:{rid}")
        if has_ctx is None and has_res is None:
            doc = key_s.split(":")[-1]
            r.delete(key_s)
            orphan_del.append((doc, rid))
            print("orphan_runlock_del", doc, rid)
    print("summary recovered=", len(recovered), "orphan_lock_del=", len(orphan_del))
    left: list[str] = []
    for key in r.scan_iter("webhook:run:context:*", count=500):
        key_s = key if isinstance(key, str) else key.decode()
        raw = r.get(key_s)
        if not raw:
            continue
        try:
            o = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if o.get("status") == "running":
            left.append(key_s)
    print("running_context_keys_left", len(left), left[:8])
    return 0 if not left else 3


if __name__ == "__main__":
    raise SystemExit(main())
