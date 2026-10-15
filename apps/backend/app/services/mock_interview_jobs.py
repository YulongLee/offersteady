"""Bounded text jobs with durable claims, no database lock across provider I/O.

Start/capture require the dedicated billing and desktop lifecycle. This
coordinator cannot create, start or charge a session.
"""
from __future__ import annotations

import asyncio
from time import monotonic, time

from app.core.errors import DomainRequestError
from app.services.mock_interview_generation import MockInterviewGenerator, MockResumeReader, MockGenerationUnavailable
from app.services.mock_interview_diagnostics import MockGenerationDiagnostics, generation_diagnostics
from app.services.mock_interview_repository import MockInterviewRepository, round_state
from app.services.mock_interview_rounds import MockRoundState


class MockInterviewJobs:
    def __init__(self, repository: MockInterviewRepository, reader: MockResumeReader,
                 generator: MockInterviewGenerator, *, now_ms=None):
        self.repository = repository
        self.reader = reader
        self.generator = generator
        self.now_ms = now_ms or (lambda: int(time() * 1000))

    async def run_pending(self, *, user_id: str, session_id: str) -> dict:
        record = await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)
        # A question may cross the duration boundary in claim, provider I/O or
        # commit. Follow its replacement report once, never loop retries.
        for attempt in range(2):
            state = round_state(record)
            if state.phase not in ("generating_question", "generating_report"):
                return record
            try:
                claimed = await asyncio.to_thread(self.repository.claim_generation, user_id=user_id,
                    session_id=session_id, operation_id=state.operation_id, now_ms=self.now_ms())
            except DomainRequestError as exc:
                if exc.error_code not in ("mock_stale_operation", "mock_generation_in_progress"):
                    raise
                current = await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)
                if self._expired_question(state, current) and exc.error_code == "mock_stale_operation":
                    record = current
                    continue
                if self._duration_ended_question(state, current):
                    return current
                # Another worker owns the report reached by our expiry. Its
                # lease is authoritative; leave completion to that worker.
                if attempt and state.phase == "generating_report" and current["data"].get("end_reason") == "time_limit":
                    return current
                raise
            claimed_state = round_state(claimed)
            if (claimed_state.phase != state.phase or claimed_state.operation_id != state.operation_id
                    or not claimed["data"].get("generation_claim")):
                record = claimed
                if self._expired_question(state, record):
                    continue
                return record
            kind = "question" if state.phase == "generating_question" else "report"
            with generation_diagnostics(self.repository.settings, kind) as diagnostics:
                record = await self._run_claimed(claimed, state, user_id=user_id, session_id=session_id,
                                                diagnostics=diagnostics)
            if not self._expired_question(state, record):
                return record
        return record

    @staticmethod
    def _duration_ended_question(state: MockRoundState, record: dict) -> bool:
        current = round_state(record)
        return (state.phase == "generating_question" and current.phase in ("generating_report", "completed")
                and current.operation_id != state.operation_id and record["data"].get("end_reason") == "time_limit")

    @classmethod
    def _expired_question(cls, state: MockRoundState, record: dict) -> bool:
        return cls._duration_ended_question(state, record) and round_state(record).phase == "generating_report"

    def _question_deadline(self, record: dict, state: MockRoundState) -> int | None:
        deadline_method = getattr(self.repository, "duration_deadline", None)
        return deadline_method(record) if state.phase == "generating_question" and callable(deadline_method) else None

    async def _expire_if_due(self, claimed: dict, state: MockRoundState, *, user_id: str,
                             session_id: str, now_ms: int | None = None) -> dict | None:
        deadline = self._question_deadline(claimed, state)
        now_ms = self.now_ms() if now_ms is None else now_ms
        if deadline is None or now_ms < deadline:
            return None
        return await asyncio.to_thread(self.repository.expire_duration,
            user_id=user_id, session_id=session_id, now_ms=now_ms)

    async def _run_claimed(self, claimed: dict, state: MockRoundState, *, user_id: str, session_id: str,
                           diagnostics: MockGenerationDiagnostics) -> dict:
        finish = dict(user_id=user_id, session_id=session_id, operation_id=state.operation_id,
                      claim_id=claimed["data"]["generation_claim"])
        started_at = monotonic()
        provider_attempted = False
        deadline = self._question_deadline(claimed, state)
        timeout_seconds = self.repository.settings.mock_interview_provider_timeout_seconds
        duration_timeout = False
        if deadline is not None:
            remaining_seconds = max(0, deadline-self.now_ms()) / 1000
            duration_timeout = remaining_seconds <= timeout_seconds
            timeout_seconds = min(timeout_seconds, remaining_seconds)
        timeout = asyncio.timeout_at(monotonic() + timeout_seconds)
        try:
            expired = await self._expire_if_due(claimed, state, user_id=user_id, session_id=session_id)
            if expired is not None:
                diagnostics.record("generation_total", started_at, outcome="cancelled", error_category="cancelled")
                return expired
            async with timeout:
                data = claimed["data"]
                # Ending preparation needs neither a selected resume nor a paid
                # model call; the generator returns an unscored evidence state.
                if state.phase == "generating_report" and not any(r.answer for r in state.rounds):
                    resume = ""
                else:
                    read_started_at = monotonic()
                    try:
                        if not data.get("resume_id") or not data.get("resume_version"):
                            raise ValueError("missing selected resume")
                        resume = await asyncio.to_thread(self.reader.read, user_id=user_id,
                            document_id=data["resume_id"], version_id=data["resume_version"])
                    except asyncio.CancelledError:
                        diagnostics.record("resume_read", read_started_at, outcome="cancelled", error_category="cancelled")
                        raise
                    except DomainRequestError:
                        diagnostics.record("resume_read", read_started_at,
                            outcome="fallback" if state.phase == "generating_report" else "failed", error_category="resume_unavailable")
                        if state.phase != "generating_report":
                            raise
                        # Deleted/changed resume cannot prevent a report of
                        # already submitted answers. Never revive deleted data.
                        resume = "[原简历版本已不可用，本报告仅依据已确认的问答。]"
                    except Exception:
                        category = "resume_read_error" if data.get("resume_id") and data.get("resume_version") else "selected_resume_missing"
                        diagnostics.record("resume_read", read_started_at, outcome="failed", error_category=category)
                        raise
                    else:
                        diagnostics.record("resume_read", read_started_at)
                args = dict(resume=resume, target_role=data["target_role"], rounds=state.rounds)
                expired = await self._expire_if_due(claimed, state, user_id=user_id, session_id=session_id)
                if expired is not None:
                    diagnostics.record("generation_total", started_at, outcome="cancelled", error_category="cancelled")
                    return expired
                provider_attempted = True
                if state.phase == "generating_question":
                    result = await self.generator.question(**args)
                    output = {"question": result.question}
                else:
                    result = await self.generator.report(**args)
                    output = {"report": result.model_dump()}
            record = await asyncio.to_thread(self.repository.finish_generation, **finish,
                now_ms=self.now_ms(), **output)
            discarded = self._duration_ended_question(state, record)
            diagnostics.record("generation_total", started_at,
                outcome="cancelled" if discarded else "success",
                error_category="cancelled" if discarded else None)
            return record
        except asyncio.CancelledError:
            # A disconnected HTTP caller cannot leave the next attempt locked
            # until restart. A bounded durable lease also covers process death.
            diagnostics.record("generation_total", started_at, outcome="cancelled", error_category="cancelled")
            await asyncio.shield(self._release_cancelled(finish, claimed, state))
            raise
        except Exception as exc:
            # Expiration is a lifecycle result, not a provider fault or refund
            # trigger. A deadline-bounded timeout fires at the known deadline
            # even when an injected clock has not advanced between awaits.
            expiry_time = self.now_ms()
            if duration_timeout and isinstance(exc, TimeoutError) and timeout.expired():
                expiry_time = max(expiry_time, deadline)
            expired = await self._expire_if_due(claimed, state, user_id=user_id,
                session_id=session_id, now_ms=expiry_time)
            if expired is not None:
                diagnostics.record("generation_total", started_at, outcome="cancelled", error_category="cancelled")
                return expired
            # Do not persist provider messages, keys or resume contents.
            provider_fault = (isinstance(exc, MockGenerationUnavailable)
                or provider_attempted and isinstance(exc, TimeoutError)
                or isinstance(exc, DomainRequestError) and exc.error_code in ("mock_repeated_question", "mock_invalid_question"))
            if isinstance(exc, MockGenerationUnavailable):
                category = exc.error_category
            elif isinstance(exc, TimeoutError):
                category = "generation_timeout"
            elif isinstance(exc, DomainRequestError):
                category = "commit_rejected" if provider_attempted else "resume_unavailable"
            elif not provider_attempted:
                category = "resume_read_error" if claimed["data"].get("resume_id") and claimed["data"].get("resume_version") else "selected_resume_missing"
            else:
                category = "internal_error"
            diagnostics.record("generation_total", started_at, outcome="failed", error_category=category,
                               http_status=exc.http_status if isinstance(exc, MockGenerationUnavailable) else None)
            await self._release_failed(finish, provider_fault=provider_fault)
            return await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)

    async def _release_cancelled(self, finish: dict, claimed: dict, state: MockRoundState) -> None:
        try:
            expired = await self._expire_if_due(claimed, state,
                user_id=finish["user_id"], session_id=finish["session_id"])
        except DomainRequestError as exc:
            if exc.error_code in ("mock_not_found", "mock_session_ended"):
                return
            raise
        if expired is None:
            await self._release_failed(finish)

    async def _release_failed(self, finish: dict, *, provider_fault: bool = False) -> None:
        try:
            await asyncio.to_thread(self.repository.finish_generation, **finish,
                now_ms=self.now_ms(), failed=True, provider_fault=provider_fault)
        except DomainRequestError as exc:
            if exc.error_code not in ("mock_stale_operation", "mock_session_ended", "mock_not_found"):
                raise
