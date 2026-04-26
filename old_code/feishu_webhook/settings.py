from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> Path:
    return Path(__file__).resolve().parents[1] / ".env"


class WebhookSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_ignore_empty=False,
    )

    redis_url: str = Field(default="redis://127.0.0.1:6381/0", alias="REDIS_URL")

    vla_host: str = Field(default="0.0.0.0", alias="VLA_HOST")
    vla_port: int = Field(default=18080, alias="VLA_PORT")
    vla_queue_name: str = Field(default="vla:default", alias="VLA_QUEUE_NAME")
    vla_rq_job_timeout_seconds: int = Field(
        default=3600,
        alias="VLA_RQ_JOB_TIMEOUT_SECONDS",
    )

    feishu_api_base: str = Field(
        default="https://open.feishu.cn",
        alias="FEISHU_API_BASE",
    )
    feishu_webhook_path: str = Field(
        default="/webhook/feishu",
        alias="FEISHU_WEBHOOK_PATH",
    )
    feishu_app_id: str = Field(default="", alias="FEISHU_APP_ID")
    feishu_app_secret: str = Field(default="", alias="FEISHU_APP_SECRET")
    feishu_encrypt_key: str = Field(default="", alias="FEISHU_ENCRYPT_KEY")
    feishu_verification_token: str = Field(
        default="",
        alias="FEISHU_VERIFICATION_TOKEN",
    )
    feishu_event_dedup_ttl_seconds: int = Field(
        default=86400,
        alias="FEISHU_EVENT_DEDUP_TTL_SECONDS",
    )
    feishu_webhook_doc_debounce_seconds: int = Field(
        default=0,
        alias="FEISHU_WEBHOOK_DOC_DEBOUNCE_SECONDS",
    )
    feishu_subscribe_folder_token: str = Field(
        default="",
        alias="FEISHU_SUBSCRIBE_FOLDER_TOKEN",
    )
    feishu_auto_subscribe_docx: bool = Field(
        default=True,
        alias="FEISHU_AUTO_SUBSCRIBE_DOCX",
    )
    feishu_presubscribe_docx_tokens: str = Field(
        default="",
        alias="FEISHU_PRESUBSCRIBE_DOCX_TOKENS",
    )
    feishu_subscribe_state_ttl_seconds: int = Field(
        default=2592000,
        alias="FEISHU_SUBSCRIBE_STATE_TTL_SECONDS",
    )

    @field_validator("feishu_api_base")
    @classmethod
    def _normalize_api_base(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("feishu_webhook_path")
    @classmethod
    def _normalize_webhook_path(cls, value: str) -> str:
        path = value.strip()
        if not path.startswith("/"):
            raise ValueError("FEISHU_WEBHOOK_PATH must start with '/'")
        return path.rstrip("/") or "/"

    @field_validator("vla_queue_name")
    @classmethod
    def _validate_queue_name(cls, value: str) -> str:
        queue_name = value.strip()
        if not queue_name:
            raise ValueError("VLA_QUEUE_NAME cannot be empty")
        return queue_name

    @model_validator(mode="after")
    def _validate_bounds(self) -> "WebhookSettings":
        if not 1 <= int(self.vla_port) <= 65535:
            raise ValueError("VLA_PORT must be between 1 and 65535")
        if int(self.vla_rq_job_timeout_seconds) <= 0:
            raise ValueError("VLA_RQ_JOB_TIMEOUT_SECONDS must be > 0")
        if int(self.feishu_event_dedup_ttl_seconds) <= 0:
            raise ValueError("FEISHU_EVENT_DEDUP_TTL_SECONDS must be > 0")
        if int(self.feishu_webhook_doc_debounce_seconds) < 0:
            raise ValueError("FEISHU_WEBHOOK_DOC_DEBOUNCE_SECONDS must be >= 0")
        if int(self.feishu_subscribe_state_ttl_seconds) <= 0:
            raise ValueError("FEISHU_SUBSCRIBE_STATE_TTL_SECONDS must be > 0")
        return self


@lru_cache
def get_webhook_settings() -> WebhookSettings:
    return WebhookSettings()

