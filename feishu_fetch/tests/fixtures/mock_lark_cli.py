from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _append_log(args: list[str]) -> None:
    log_path = os.environ.get("MOCK_LARK_LOG")
    if not log_path:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {"argv0": sys.argv[0], "args": args},
                ensure_ascii=False,
            )
            + "\n"
        )


def _main() -> int:
    args = sys.argv[1:]
    _append_log(args)

    if args == ["--help"]:
        sys.stdout.write("mock lark-cli help\n")
        return 0

    if len(args) >= 3 and args[0] == "docs" and args[1] == "+fetch":
        try:
            document_id = args[args.index("--document-id") + 1]
        except (ValueError, IndexError):
            sys.stderr.write("missing --document-id\n")
            return 2

        payload = {
            "data": {
                "document": {
                    "title": "Local Mock",
                    "content": "<doc><p>Local Mock</p></doc>",
                    "document_id": document_id,
                }
            }
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False))
        return 0

    sys.stderr.write(f"unsupported mock args: {args}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
