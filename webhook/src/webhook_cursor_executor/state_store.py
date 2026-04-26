from __future__ import annotations

import time

from redis import Redis

from webhook_cursor_executor.models import (
    DocumentSnapshot,
    RerunMarker,
    RunContext,
    RunResult,
)


class RedisStateStore:
    def __init__(
        self,
        *,
        redis_client: Redis,
        event_seen_ttl_seconds: int = 86400,
        snapshot_ttl_seconds: int = 86400,
        rerun_ttl_seconds: int = 86400,
        run_context_ttl_seconds: int = 259200,
        run_result_ttl_seconds: int = 259200,
    ) -> None:
        self.redis = redis_client
        self.event_seen_ttl_seconds = event_seen_ttl_seconds
        self.snapshot_ttl_seconds = snapshot_ttl_seconds
        self.rerun_ttl_seconds = rerun_ttl_seconds
        self.run_context_ttl_seconds = run_context_ttl_seconds
        self.run_result_ttl_seconds = run_result_ttl_seconds

    def _event_seen_key(self, event_id: str) -> str:
        return f"webhook:event_seen:{event_id}"

    def _snapshot_key(self, document_id: str) -> str:
        return f"webhook:doc:snapshot:{document_id}"

    def _version_key(self, document_id: str) -> str:
        return f"webhook:doc:version:{document_id}"

    def _runlock_key(self, document_id: str) -> str:
        return f"webhook:doc:runlock:{document_id}"

    def _rerun_key(self, document_id: str) -> str:
        return f"webhook:doc:rerun:{document_id}"

    def _run_context_key(self, run_id: str) -> str:
        return f"webhook:run:context:{run_id}"

    def _run_result_key(self, run_id: str) -> str:
        return f"webhook:run:result:{run_id}"

    def try_mark_event_seen(self, event_id: str) -> bool:
        return bool(
            self.redis.set(
                self._event_seen_key(event_id),
                "1",
                nx=True,
                ex=self.event_seen_ttl_seconds,
            )
        )

    def next_version(self, document_id: str) -> int:
        value = int(self.redis.incr(self._version_key(document_id)))
        self.redis.expire(self._version_key(document_id), self.snapshot_ttl_seconds)
        return value

    def save_snapshot(self, snapshot: DocumentSnapshot) -> None:
        self.redis.set(
            self._snapshot_key(snapshot.document_id),
            snapshot.model_dump_json(),
            ex=self.snapshot_ttl_seconds,
        )

    def load_snapshot(self, document_id: str) -> DocumentSnapshot | None:
        raw = self.redis.get(self._snapshot_key(document_id))
        return None if raw is None else DocumentSnapshot.model_validate_json(raw)

    def try_acquire_runlock(
        self,
        *,
        document_id: str,
        run_id: str,
        ttl_seconds: int,
    ) -> bool:
        return bool(
            self.redis.set(
                self._runlock_key(document_id),
                run_id,
                nx=True,
                ex=ttl_seconds,
            )
        )

    def runlock_owned_by(self, *, document_id: str, run_id: str) -> bool:
        return self.redis.get(self._runlock_key(document_id)) == run_id

    def release_runlock(self, *, document_id: str, run_id: str) -> None:
        if self.runlock_owned_by(document_id=document_id, run_id=run_id):
            self.redis.delete(self._runlock_key(document_id))

    def mark_rerun(self, *, document_id: str, target_version: int) -> None:
        marker = RerunMarker(target_version=target_version, updated_at=int(time.time()))
        self.redis.set(
            self._rerun_key(document_id),
            marker.model_dump_json(),
            ex=self.rerun_ttl_seconds,
        )

    def get_rerun(self, document_id: str) -> RerunMarker | None:
        raw = self.redis.get(self._rerun_key(document_id))
        return None if raw is None else RerunMarker.model_validate_json(raw)

    def clear_rerun(self, document_id: str) -> None:
        self.redis.delete(self._rerun_key(document_id))

    def save_run_context(self, context: RunContext) -> None:
        self.redis.set(
            self._run_context_key(context.run_id),
            context.model_dump_json(),
            ex=self.run_context_ttl_seconds,
        )

    def clear_run_context(self, run_id: str) -> None:
        self.redis.delete(self._run_context_key(run_id))

    def save_run_result(self, result: RunResult) -> None:
        self.redis.set(
            self._run_result_key(result.run_id),
            result.model_dump_json(),
            ex=self.run_result_ttl_seconds,
        )

    def load_run_result(self, run_id: str) -> RunResult | None:
        raw = self.redis.get(self._run_result_key(run_id))
        return None if raw is None else RunResult.model_validate_json(raw)
