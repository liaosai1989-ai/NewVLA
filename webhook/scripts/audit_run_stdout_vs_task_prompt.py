"""事故复盘：`webhook:run:result:<run_id>.summary` 与当次磁盘 `task_prompt.md` 的可重复对齐证据。

**证明目标**（二选一表述即可成立）：
- `summary` 与 **`task_prompt.md` 正文不等** → 服务端持久化的「Agent 报告」≠ 本轮注入文案；
- 或：`summary` 中出现 **异于本 `run_id` 的路径/会话标识** → 会话串线在文本层可复述。

**与「原始 OS 管道字节」的差距**（实现真源：`webhook_cursor_executor.cursor_cli.launch_cursor_agent`）：

1. Redis 仅存 ``RunResult.summary`` = ``stdout.strip() or stderr.strip()``：**首尾空白丢失**；
2. stdout 非空（strip 后）时：**stderr 不进入 Redis**；
3. ``subprocess`` 解码用过 ``encoding="utf-8", errors="replace"``：非法字节已替换，不等于内核原始 FD。

因此本脚本对齐的是「**服务端所保留的 UTF-8 文本**」，不是未经 strip 的二进制快照；需在复盘文档中注明上述链路。

用法（执行工作区根含 ``.env`` 与 ``REDIS_URL``）：

    py -3.12 scripts/audit_run_stdout_vs_task_prompt.py --workspace-root C:\\VLA_Workplace --run-id 04978895-5218-4ac2-85c8-958d41190df5

输出：单行 JSON（UTF-8），便于粘贴 / ``sha256sum`` 对拍。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    from redis import Redis
except ImportError as exc:  # pragma: no cover
    print("redis package required", file=sys.stderr)
    raise SystemExit(2) from exc

_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def _parse_env_redis_url(workspace_root: Path) -> str:
    env_path = workspace_root / ".env"
    if not env_path.is_file():
        raise FileNotFoundError(f"missing {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == "REDIS_URL":
            return (
                v.strip()
                .strip('"')
                .strip("'")
            )
    raise ValueError("REDIS_URL not in workspace .env")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _uuid_set(text: str) -> frozenset[str]:
    hits = {(m.group(0).lower()) for m in _UUID_RE.finditer(text)}
    return frozenset(hits)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Align Redis RunResult.summary vs task_prompt.md")
    p.add_argument(
        "--workspace-root",
        type=Path,
        required=True,
        help="物化执行工作区根（含 .env/.cursor_task）",
    )
    p.add_argument("--run-id", required=True, help="单次任务 run_id（uuid）")
    args = p.parse_args(argv)

    ws: Path = args.workspace_root.expanduser().resolve()
    rid: str = str(args.run_id).strip()
    url = _parse_env_redis_url(ws)
    redis = Redis.from_url(url, decode_responses=True)
    raw = redis.get(f"webhook:run:result:{rid}")
    if raw is None:
        print(json.dumps({"error": "redis_miss", "redis_key": f"webhook:run:result:{rid}"}, ensure_ascii=False))
        return 1

    result = json.loads(raw)
    summary = result.get("summary") or ""
    if not isinstance(summary, str):
        print(json.dumps({"error": "summary_not_str", "result_keys": sorted(result.keys())}, ensure_ascii=False))
        return 1

    tp = ws / ".cursor_task" / rid / "task_prompt.md"
    if not tp.is_file():
        prompt_text = ""
        prompt_present = False
    else:
        prompt_text = tp.read_text(encoding="utf-8")
        prompt_present = True

    sum_utf8 = summary.encode("utf-8")
    pr_utf8 = prompt_text.encode("utf-8")

    uuids_in_summary = _uuid_set(summary)
    uuids_in_prompt = _uuid_set(prompt_text)
    expected_lower = rid.lower()

    alien_in_summary = sorted(x for x in uuids_in_summary if x != expected_lower)

    out: dict = {
        "evidence_version": "1",
        "run_id": rid,
        "redis_key": f"webhook:run:result:{rid}",
        "persisted_capture": {
            "field": "summary",
            "implementation_note": "stdout.strip() or stderr.strip(); stderr dropped if stripped stdout nonempty — cursor_cli.launch_cursor_agent",
            "sha256_utf8_hex": _sha256_hex(sum_utf8),
            "byte_length": len(sum_utf8),
            "newline_count": summary.count("\n"),
        },
        "task_prompt": {
            "path": str(tp) if prompt_present else None,
            "present": prompt_present,
            "sha256_utf8_hex": _sha256_hex(pr_utf8) if prompt_present else None,
            "byte_length": len(pr_utf8) if prompt_present else 0,
        },
        "uuid_tokens": {
            "in_summary_not_equal_run_id": alien_in_summary,
            "intersection_prompt_and_summary_uuid_sets": sorted(
                x for x in (uuids_in_summary & uuids_in_prompt)
            ),
        },
        "texts_equal_utf8": (summary == prompt_text) if prompt_present else None,
        "verdict_hints": [
            *(
                [{"code": "TASK_PROMPT_MISSING_ON_DISK", "path": str(tp)}]
                if not prompt_present
                else []
            ),
            *(
                [{"code": "SUMMARY_CONTAINS_UUIDS_OTHER_THAN_RUN_ID", "foreign": alien_in_summary}]
                if alien_in_summary
                else []
            ),
            *(
                [
                    {
                        "code": "SUMMARY_NOT_EQUAL_TASK_PROMPT_BODY",
                        "expected_for_replay": "prove agent output != injected instruction file",
                    }
                ]
                if prompt_present and summary != prompt_text
                else []
            ),
        ],
    }

    print(json.dumps(out, ensure_ascii=False, indent=None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
