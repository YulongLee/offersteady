from __future__ import annotations

from typing import Protocol


class DocumentParsingPort(Protocol):
    def parse(self, *, resource_id: str) -> None: ...


class NullDocumentParsingPort:
    def parse(self, *, resource_id: str) -> None:
        return None
