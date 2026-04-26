from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeishuFetchError(RuntimeError):
    code: str
    llm_message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.llm_message


def build_error(
    *,
    code: str,
    reason: str,
    advice: str,
    detail: dict[str, Any] | None = None,
) -> FeishuFetchError:
    return FeishuFetchError(
        code=code,
        llm_message=f"飞书正文抓取失败：{reason}。\n处理建议：{advice}。",
        detail=detail or {},
    )
