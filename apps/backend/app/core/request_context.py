from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RequestContext:
    request_id: str
