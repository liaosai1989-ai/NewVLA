from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# code 合同：dependency_error、lark_config_error、permission_error、runtime_error、
# empty_content、request_error 等；勿混用 §10.1–10.3 与文首映射表。

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
