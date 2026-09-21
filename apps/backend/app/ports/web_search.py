from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class WebSearchSource:
    title: str
    url: str
    snippet: str = ""
    retrieved_at_ms: int = 0


@dataclass(frozen=True)
class WebSearchAnswer:
    answer_text: str
    sources: list[WebSearchSource] = field(default_factory=list)
    status: str = "succeeded"
    provider: str = "dashscope-responses"
    duration_ms: int = 0
    safe_error_code: str | None = None


class WebSearchGatewayPort(Protocol):
    def answer(
        self,
        *,
        question: str,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        language: str,
    ) -> WebSearchAnswer: ...
