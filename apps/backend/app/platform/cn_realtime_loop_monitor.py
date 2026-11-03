"""Bounded, content-free scheduling observations for the CN application loop."""
from __future__ import annotations

import asyncio
from collections import deque
import json
import logging
from math import ceil, isfinite
from threading import Lock
from time import perf_counter
from typing import Awaitable, Callable


_logger = logging.getLogger("offersteady.backend.cn_main_loop")


class CnMainLoopMonitor:
    """Observe scheduler drift, not an individual request's execution time.

    The timer resets after each observation rather than trying to catch up after
    a pause. Samples contain no request, user, device, session or audio data.
    """

    def __init__(
        self,
        *,
        interval_seconds: float = 0.25,
        max_samples: int = 512,
        emit_every: int = 120,
        clock: Callable[[], float] = perf_counter,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._interval = max(0.01, float(interval_seconds))
        self._values: deque[float] = deque(maxlen=max(1, min(4096, max_samples)))
        self._emit_every = max(1, emit_every)
        self._clock = clock
        self._sleep = sleep
        self._lock = Lock()
        self._observations = 0

    def _now(self) -> float | None:
        try:
            value = self._clock()
            return value if isfinite(value) else None
        except Exception:
            return None

    def observe(self, delay_ms: float) -> None:
        """Ignore broken observations; telemetry must never alter runtime work."""
        try:
            if not isfinite(delay_ms) or delay_ms < 0:
                return
            with self._lock:
                self._values.append(round(delay_ms, 3))
                self._observations += 1
                emit = self._observations % self._emit_every == 0
            if emit:
                self._emit()
        except Exception:
            pass

    def summary(self) -> dict[str, int | float]:
        with self._lock:
            values = sorted(self._values)
            observations = self._observations
        count = len(values)
        return {
            "sampleCount": count,
            "observations": observations,
            "capacity": self._values.maxlen or 0,
            "intervalMs": round(self._interval * 1000, 3),
            "p50Ms": values[max(0, ceil(count * 0.5) - 1)] if count else 0.0,
            "p95Ms": values[max(0, ceil(count * 0.95) - 1)] if count else 0.0,
            "maxMs": values[-1] if count else 0.0,
            "over50Ms": sum(value >= 50 for value in values),
            "over250Ms": sum(value >= 250 for value in values),
        }

    def _emit(self) -> None:
        try:
            _logger.info(
                "cn_main_loop_timing %s",
                json.dumps({"schema": 1, **self.summary()}, separators=(",", ":"), allow_nan=False),
            )
        except Exception:
            pass

    async def run(self) -> None:
        previous = self._now()
        while True:
            # Cancellation is deliberately propagated; no shutdown timer survives
            # the application lifespan. asyncio.sleep never performs blocking I/O.
            await self._sleep(self._interval)
            current = self._now()
            if current is not None and previous is not None:
                self.observe(max(0.0, (current - previous - self._interval) * 1000))
            previous = current
