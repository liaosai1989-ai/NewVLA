from __future__ import annotations

from pydantic import BaseModel


class DocumentSnapshot(BaseModel):
    event_id: str
    document_id: str
    folder_token: str
    event_type: str
    qa_rule_file: str
    dataset_id: str
    workspace_path: str
    cursor_timeout_seconds: int
    received_at: str
    version: int
    dify_target_key: str = "DEFAULT"
    ingest_kind: str


class RerunMarker(BaseModel):
    required: bool = True
    target_version: int
    updated_at: int


class RunContext(BaseModel):
    run_id: str
    document_id: str
    version: int
    event_id: str
    workspace_path: str
    status: str


class RunResult(BaseModel):
    run_id: str
    document_id: str
    version: int
    exit_code: int
    status: str
    summary: str | None = None


class TaskContext(BaseModel):
    schema_version: str
    run_id: str
    event_id: str
    document_id: str
    folder_token: str
    event_type: str
    snapshot_version: int
    qa_rule_file: str
    dataset_id: str
    workspace_path: str
    trigger_source: str
    received_at: str
    cursor_timeout_seconds: int
    dify_target_key: str
    ingest_kind: str
    dataset_id_is_placeholder: bool = False
