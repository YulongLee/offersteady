from __future__ import annotations

from typing import Protocol


class StreamingPort(Protocol):
    def publish(self, *, session_id: str, event_name: str) -> None: ...


class NullStreamingPort:
    def publish(self, *, session_id: str, event_name: str) -> None:
        return None
