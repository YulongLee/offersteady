from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class PersistedPointsLedgerEntry:
    id: str
    user_id: str
    kind: str
    points: int
    created_at_ms: int
    reference_id: str
    description: str


@dataclass(frozen=True)
class PersistedPointsRedemption:
    redemption_id: str
    points: int
    persisted_balance: int
    public_hint: str
    redeemed_at_ms: int
    ledger_entry: PersistedPointsLedgerEntry


@dataclass(frozen=True)
class PersistedRedemptionResult:
    outcome: str
    redemption: PersistedPointsRedemption | None = None


class PointsRedemptionRepository(Protocol):
    def sync_configured_codes(self, codes: Mapping[str, int]) -> None: ...

    def redeem(self, *, user_id: str, code: str, idempotency_key: str) -> PersistedRedemptionResult: ...

    def list_ledger(self, *, user_id: str) -> list[PersistedPointsLedgerEntry]: ...

    def balance(self, *, user_id: str) -> int: ...
