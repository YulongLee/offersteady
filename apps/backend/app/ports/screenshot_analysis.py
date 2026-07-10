from __future__ import annotations

from typing import Protocol


class ScreenshotAnalysisPort(Protocol):
    def enqueue(self, *, session_id: str, filename: str) -> str: ...


class NullScreenshotAnalysisPort:
    def enqueue(self, *, session_id: str, filename: str) -> str:
        return f"placeholder-screenshot-task:{session_id}:{filename}"
