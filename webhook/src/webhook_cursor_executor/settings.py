from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


class PipelineWorkspace(BaseModel):
    path: str
    cursor_timeout_seconds: int = 7200


class FolderRoute(BaseModel):
    folder_token: str
    qa_rule_file: str
    dataset_id: str


class RoutingConfig(BaseModel):
    pipeline_workspace: PipelineWorkspace
    folder_routes: list[FolderRoute]


class ExecutorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    redis_url: str = Field(default="redis://127.0.0.1:6381/0", alias="REDIS_URL")
    vla_queue_name: str = Field(default="vla:default", alias="VLA_QUEUE_NAME")
    feishu_webhook_path: str = Field(
        default="/webhook/feishu",
        alias="FEISHU_WEBHOOK_PATH",
    )
    feishu_encrypt_key: str = Field(default="", alias="FEISHU_ENCRYPT_KEY")
    feishu_verification_token: str = Field(
        default="",
        alias="FEISHU_VERIFICATION_TOKEN",
    )

    event_seen_ttl_seconds: int = Field(default=86400, alias="EVENT_SEEN_TTL_SECONDS")
    doc_snapshot_ttl_seconds: int = Field(
        default=86400,
        alias="DOC_SNAPSHOT_TTL_SECONDS",
    )
    doc_runlock_ttl_seconds: int = Field(
        default=10800,
        alias="DOC_RUNLOCK_TTL_SECONDS",
    )
    doc_rerun_ttl_seconds: int = Field(default=86400, alias="DOC_RERUN_TTL_SECONDS")
    run_context_ttl_seconds: int = Field(
        default=259200,
        alias="RUN_CONTEXT_TTL_SECONDS",
    )
    run_result_ttl_seconds: int = Field(
        default=259200,
        alias="RUN_RESULT_TTL_SECONDS",
    )
    cursor_run_timeout_seconds: int = Field(
        default=7200,
        alias="CURSOR_RUN_TIMEOUT_SECONDS",
    )

    folder_routes_file: str = Field(
        default=str(
            Path(__file__).resolve().parents[2]
            / "config"
            / "folder_routes.example.json"
        ),
        alias="FOLDER_ROUTES_FILE",
    )
    cursor_cli_model: str = Field(default="composer-2-fast", alias="CURSOR_CLI_MODEL")
    cursor_cli_command: str = Field(default="cursor", alias="CURSOR_CLI_COMMAND")
    cursor_cli_config_path: str = Field(
        default=str(Path.home() / ".cursor" / "cli-config.json"),
        alias="CURSOR_CLI_CONFIG_PATH",
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> "ExecutorSettings":
        if self.doc_runlock_ttl_seconds < self.cursor_run_timeout_seconds:
            raise ValueError(
                "DOC_RUNLOCK_TTL_SECONDS must be >= CURSOR_RUN_TIMEOUT_SECONDS"
            )
        return self


def load_routing_config(settings: ExecutorSettings) -> RoutingConfig:
    data = json.loads(Path(settings.folder_routes_file).read_text(encoding="utf-8"))
    return RoutingConfig.model_validate(data)


@lru_cache
def get_executor_settings() -> ExecutorSettings:
    return ExecutorSettings()
