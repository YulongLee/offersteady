from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from secrets import token_urlsafe
import threading
from time import monotonic
from typing import Callable


@dataclass(frozen=True, slots=True)
class ScreenshotStreamLease:
    device_id: str
    token: str


@dataclass(frozen=True, slots=True)
class ScreenshotStreamAdmissionDecision:
    admitted: bool
    lease: ScreenshotStreamLease | None = None
    reason: str | None = None
    retry_after_ms: int = 0


class ScreenshotStreamAdmissionCoordinator:
    """Bound screenshot SSE ownership without changing stream semantics."""

    def __init__(
        self,
        *,
        max_active: int,
        reconnect_window_seconds: float,
        reconnect_max_accepts: int,
        retry_after_seconds: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._max_active = max(1, max_active)
        self._reconnect_window_seconds = max(0.1, reconnect_window_seconds)
        self._reconnect_max_accepts = max(1, reconnect_max_accepts)
        self._retry_after_ms = max(1, retry_after_seconds) * 1_000
        self._clock = clock
        self._lock = threading.Lock()
        self._active: dict[str, ScreenshotStreamLease] = {}
        self._accepted_at: dict[str, deque[float]] = {}
        self._last_history_cleanup_at = self._clock()
        self._accepted = 0
        self._released = 0
        self._duplicate_denied = 0
        self._reconnect_rate_denied = 0
        self._global_capacity_denied = 0
        self._max_active_observed = 0
        self._closed = False

    def acquire(self, device_id: str) -> ScreenshotStreamAdmissionDecision:
        now = self._clock()
        with self._lock:
            self._cleanup_expired_history(now)
            if self._closed:
                self._global_capacity_denied += 1
                return self._denied("global-capacity")
            if device_id in self._active:
                self._duplicate_denied += 1
                return self._denied("duplicate")

            accepted_at = self._accepted_at.setdefault(device_id, deque())
            cutoff = now - self._reconnect_window_seconds
            while accepted_at and accepted_at[0] <= cutoff:
                accepted_at.popleft()
            if len(accepted_at) >= self._reconnect_max_accepts:
                self._reconnect_rate_denied += 1
                return self._denied("reconnect-rate")
            if len(self._active) >= self._max_active:
                self._global_capacity_denied += 1
                return self._denied("global-capacity")

            lease = ScreenshotStreamLease(device_id=device_id, token=token_urlsafe(18))
            self._active[device_id] = lease
            accepted_at.append(now)
            self._accepted += 1
            self._max_active_observed = max(self._max_active_observed, len(self._active))
            return ScreenshotStreamAdmissionDecision(admitted=True, lease=lease)

    def _cleanup_expired_history(self, now: float) -> None:
        if now - self._last_history_cleanup_at < self._reconnect_window_seconds:
            return
        cutoff = now - self._reconnect_window_seconds
        expired_devices = [
            device_id
            for device_id, accepted_at in self._accepted_at.items()
            if device_id not in self._active and (not accepted_at or accepted_at[-1] <= cutoff)
        ]
        for device_id in expired_devices:
            self._accepted_at.pop(device_id, None)
        self._last_history_cleanup_at = now

    def _denied(self, reason: str) -> ScreenshotStreamAdmissionDecision:
        return ScreenshotStreamAdmissionDecision(
            admitted=False,
            reason=reason,
            retry_after_ms=self._retry_after_ms,
        )

    def release(self, lease: ScreenshotStreamLease | None) -> bool:
        if lease is None:
            return False
        with self._lock:
            current = self._active.get(lease.device_id)
            if current is None or current.token != lease.token:
                return False
            self._active.pop(lease.device_id, None)
            self._released += 1
            return True

    def diagnostics(self) -> dict[str, int]:
        with self._lock:
            return {
                "active": len(self._active),
                "maxActive": self._max_active_observed,
                "accepted": self._accepted,
                "released": self._released,
                "duplicateDenied": self._duplicate_denied,
                "reconnectRateDenied": self._reconnect_rate_denied,
                "globalCapacityDenied": self._global_capacity_denied,
                "configuredMaxActive": self._max_active,
                "retryAfterMs": self._retry_after_ms,
            }

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._released += len(self._active)
            self._active.clear()
            self._accepted_at.clear()
