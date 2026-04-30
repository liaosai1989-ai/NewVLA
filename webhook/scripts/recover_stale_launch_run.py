"""Ops: 对仍占 runlock 的僵尸 launch 补一次 finalize（清锁、可触发 rerun 再 schedule）。

环境: 设置 ``VLA_WORKSPACE_ROOT`` 为执行工作区根；在维护仓 ``webhook/`` 下::

    $env:VLA_WORKSPACE_ROOT = \"C:\\VLA_Workplace\"
    $env:PYTHONPATH = \"$(Resolve-Path .\\src);$(Resolve-Path ..\\vla_env_contract\\src)\"
    py -3.12 scripts\\recover_stale_launch_run.py <run_id>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: recover_stale_launch_run.py <run_id>", file=sys.stderr)
        return 2
    run_id = sys.argv[1].strip()
    if not os.environ.get("VLA_WORKSPACE_ROOT", "").strip():
        print("VLA_WORKSPACE_ROOT must be set to workspace root", file=sys.stderr)
        return 2

    src = Path(__file__).resolve().parents[1] / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))

    from webhook_cursor_executor.scheduler import recover_stale_launch
    from webhook_cursor_executor.worker import build_worker_runtime

    _, store, queue = build_worker_runtime()
    ok = recover_stale_launch(
        run_id=run_id,
        state_store=store,
        queue=queue,
        summary="recovered_stale_launch:recover_stale_launch_run.py",
    )
    if not ok:
        print(
            "recover_stale_launch: no running context or runlock not held by run_id",
            file=sys.stderr,
        )
        return 1
    print("ok", run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
