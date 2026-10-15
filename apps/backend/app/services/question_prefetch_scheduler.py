from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field, replace
from time import monotonic
from typing import Callable


@dataclass(frozen=True)
class _Request:
    token: int
    user_id: str
    session_id: str
    question_id: str
    revision: int
    question: str
    is_final: bool
    submitted_at: float

    @property
    def key(self) -> tuple[str, str, str]:
        return self.user_id, self.session_id, self.question_id


@dataclass
class _QuestionState:
    latest: _Request | None = None
    pending: _Request | None = None
    running: dict[int, _Request] = field(default_factory=dict)
    pending_since: float = 0
    ready_at: float = 0
    touched_at: float = 0
    started: bool = False


class QuestionPrefetchScheduler:
    """A bounded optional-work queue, independent of transcript persistence.

    Workers claim directly from per-question state. There is no executor queue
    hiding obsolete revisions, and no scheduling lock is held during retrieval.
    A final can use an idle second worker while its obsolete partial finishes.
    """

    def __init__(
        self,
        operation: Callable[..., object],
        *,
        logger: logging.Logger,
        worker_count: int = 2,
        max_keys: int = 256,
        quiet_seconds: float = 0.35,
        max_wait_seconds: float = 1.5,
        pending_ttl_seconds: float = 10,
        state_ttl_seconds: float = 120,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._operation = operation
        self._logger = logger
        self._worker_limit = min(2, max(1, worker_count))
        self._max_keys = max(1, max_keys)
        self._quiet_seconds = max(0, quiet_seconds)
        self._max_wait_seconds = max(0, max_wait_seconds)
        self._pending_ttl_seconds = max(0, pending_ttl_seconds)
        self._state_ttl_seconds = max(0, state_ttl_seconds)
        self._clock = clock
        self._condition = threading.Condition()
        self._states: dict[tuple[str, str, str], _QuestionState] = {}
        self._threads: list[threading.Thread] = []
        self._closed = False
        self._sequence = 0
        self._counts = {
            "submitted": 0, "coalesced": 0, "started": 0,
            "completed": 0, "failed": 0, "staleRejected": 0,
            "expired": 0, "overflow": 0, "cleared": 0,
            "maxActive": 0, "maxPending": 0, "maxKeys": 0,
        }

    def submit(
        self,
        *,
        user_id: str,
        session_id: str,
        question_id: str,
        revision: int,
        question: str,
        is_final: bool = False,
    ) -> bool:
        question = question.strip()
        if not user_id or not session_id or not question_id or not question:
            return False
        with self._condition:
            if self._closed:
                return False
            now = self._clock()
            self._expire_locked(now)
            key = user_id, session_id, question_id
            state = self._states.get(key)
            if state is None:
                if len(self._states) >= self._max_keys:
                    idle = [(value.touched_at, item) for item, value in self._states.items()
                            if not value.running and value.pending is None]
                    if idle:
                        self._states.pop(min(idle)[1], None)
                    else:
                        self._counts["overflow"] += 1
                        return False
                state = self._states[key] = _QuestionState(touched_at=now)
            previous = state.latest
            if (previous is not None and revision == previous.revision
                    and question == previous.question and is_final and not previous.is_final):
                # A terminal hint can share an ASR revision. Keep the token of
                # identical in-flight retrieval instead of invalidating work
                # that the cache will correctly deduplicate.
                promoted = replace(previous, is_final=True)
                state.latest = promoted
                if state.pending is not None and state.pending.token == promoted.token:
                    state.pending = promoted
                    state.ready_at = now
                state.touched_at = now
                self._condition.notify_all()
                return True
            if previous is not None and (
                revision < previous.revision
                or (previous.is_final and not is_final)
                or (revision == previous.revision and (previous.is_final or not is_final))
            ):
                self._counts["staleRejected"] += 1
                return False
            self._sequence += 1
            request = _Request(self._sequence, user_id, session_id, question_id,
                               revision, question, is_final, now)
            if state.pending is not None:
                self._counts["coalesced"] += 1
            else:
                state.pending_since = now
            state.latest = state.pending = request
            state.touched_at = now
            state.ready_at = now if is_final or not state.started else min(
                now + self._quiet_seconds,
                state.pending_since + self._max_wait_seconds,
            )
            self._counts["submitted"] += 1
            self._counts["maxKeys"] = max(self._counts["maxKeys"], len(self._states))
            self._counts["maxPending"] = max(self._counts["maxPending"], sum(
                item.pending is not None for item in self._states.values()
            ))
            # Allocate no threads until optional preparation is actually used.
            if not self._threads:
                for index in range(self._worker_limit):
                    worker = threading.Thread(target=self._work, daemon=True,
                                              name=f"question-prefetch-{index + 1}")
                    self._threads.append(worker)
                    worker.start()
            self._condition.notify_all()
            return True

    def _expire_locked(self, now: float) -> None:
        for key, state in tuple(self._states.items()):
            pending = state.pending
            if pending is not None and now - pending.submitted_at >= self._pending_ttl_seconds:
                state.pending = None
                if state.latest is pending:
                    state.latest = None
                self._counts["expired"] += 1
            if not state.running and state.pending is None and (
                state.latest is None or now - state.touched_at >= self._state_ttl_seconds
            ):
                self._states.pop(key, None)

    @staticmethod
    def _can_start(state: _QuestionState) -> bool:
        return bool(state.pending is not None and (
            not state.running or (state.pending.is_final and len(state.running) < 2)
        ))

    def _is_current(self, request: _Request) -> bool:
        with self._condition:
            state = self._states.get(request.key)
            return bool(not self._closed and state is not None and state.latest is not None
                        and state.latest.token == request.token)

    def _work(self) -> None:
        while True:
            with self._condition:
                while True:
                    if self._closed:
                        return
                    now = self._clock()
                    self._expire_locked(now)
                    eligible = [state for state in self._states.values() if self._can_start(state)]
                    ready = [state for state in eligible if state.ready_at <= now]
                    if ready:
                        state = min(ready, key=lambda item: (
                            not item.pending.is_final, item.ready_at, item.pending_since,
                        ))
                        request = state.pending
                        assert request is not None
                        state.pending = None
                        state.running[request.token] = request
                        state.started = True
                        self._counts["started"] += 1
                        self._counts["maxActive"] = max(self._counts["maxActive"], sum(
                            len(item.running) for item in self._states.values()
                        ))
                        break
                    timeout = min((max(0, state.ready_at - now) for state in eligible), default=None)
                    self._condition.wait(timeout=timeout)
            try:
                if self._is_current(request):
                    self._operation(
                        user_id=request.user_id, session_id=request.session_id,
                        question_id=request.question_id, revision=request.revision,
                        question=request.question, is_current=lambda request=request: self._is_current(request),
                    )
            except Exception as exc:
                with self._condition:
                    self._counts["failed"] += 1
                self._logger.info("realtime_speech.question_prefetch_failed",
                                  extra={"safe_error_code": exc.__class__.__name__})
            finally:
                with self._condition:
                    state = self._states.get(request.key)
                    if state is not None:
                        state.running.pop(request.token, None)
                        state.touched_at = self._clock()
                    self._counts["completed"] += 1
                    self._expire_locked(self._clock())
                    self._condition.notify_all()

    def clear_session(self, *, session_id: str) -> None:
        with self._condition:
            for key, state in tuple(self._states.items()):
                if key[1] != session_id:
                    continue
                self._counts["cleared"] += int(state.pending is not None)
                state.pending = state.latest = None
                if not state.running:
                    self._states.pop(key, None)
            self._condition.notify_all()

    def diagnostics(self) -> dict[str, int]:
        with self._condition:
            return {
                **self._counts,
                "active": sum(len(state.running) for state in self._states.values()),
                "pending": sum(state.pending is not None for state in self._states.values()),
                "keys": len(self._states),
                "workers": sum(worker.is_alive() for worker in self._threads),
            }

    def shutdown(self, *, wait: bool = False) -> None:
        with self._condition:
            self._closed = True
            for state in self._states.values():
                self._counts["cleared"] += int(state.pending is not None)
                state.pending = state.latest = None
            self._expire_locked(self._clock())
            self._condition.notify_all()
        if wait:
            for worker in self._threads:
                if worker is not threading.current_thread():
                    worker.join()
