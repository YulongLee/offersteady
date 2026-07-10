from __future__ import annotations

from typing import Protocol


class AnswerGenerationPort(Protocol):
    def start(self, *, session_id: str, prompt: str) -> str: ...


class NullAnswerGenerationPort:
    def start(self, *, session_id: str, prompt: str) -> str:
        return f"placeholder-answer-task:{session_id}"
