"""Bounded text jobs with durable claims, no database lock across provider I/O.

Start/capture require the dedicated billing and desktop lifecycle. This
coordinator cannot create, start or charge a session.
"""
from __future__ import annotations

import asyncio
from time import monotonic, time

from app.core.errors import DomainRequestError
from app.services.mock_interview_generation import MockInterviewGenerator, MockResumeReader, MockGenerationUnavailable
from app.services.mock_interview_repository import MockInterviewRepository, round_state
from app.services.mock_interview_rounds import MockRoundState
from app.services.mock_interview_diagnostics import MockGenerationDiagnostics


class MockInterviewJobs:
    def __init__(self, repository: MockInterviewRepository, reader: MockResumeReader,
                 generator: MockInterviewGenerator, *, now_ms=None):
        self.repository = repository
        self.reader = reader
        self.generator = generator
        self.now_ms = now_ms or (lambda: int(time() * 1000))

    async def run_pending(self, *, user_id: str, session_id: str) -> dict:
        record = await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)
        for attempt in range(2):
            state = round_state(record)
            if state.phase not in ('generating_question', 'generating_report'):
                return record
            try:
                claimed = await asyncio.to_thread(self.repository.claim_generation, user_id=user_id, session_id=session_id, operation_id=state.operation_id, now_ms=self.now_ms())
            except DomainRequestError as exc:
                if exc.error_code not in ('mock_stale_operation', 'mock_generation_in_progress'):
                    raise
                current = await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)
                if self._expired_question(state, current) and exc.error_code == 'mock_stale_operation':
                    record = current
                    continue
                if self._duration_ended_question(state, current):
                    return current
                if attempt and state.phase == 'generating_report' and (current['data'].get('end_reason') == 'time_limit'):
                    return current
                raise
            claimed_state = round_state(claimed)
            if claimed_state.phase != state.phase or claimed_state.operation_id != state.operation_id or (not claimed['data'].get('generation_claim')):
                record = claimed
                if self._expired_question(state, record):
                    continue
                return record
            kind = 'question' if state.phase == 'generating_question' else 'report'
            record = await self._run_claimed(claimed, state, user_id=user_id, session_id=session_id)
            if not self._expired_question(state, record):
                return record
        return record

    async def _release_failed(self, finish: dict, *, provider_fault: bool = False) -> None:
        try:
            await asyncio.to_thread(self.repository.finish_generation, **finish,
                now_ms=self.now_ms(), failed=True, provider_fault=provider_fault)
        except DomainRequestError as exc:
            if exc.error_code not in ("mock_stale_operation", "mock_session_ended", "mock_not_found"):
                raise

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

    async def _expire_if_due(self, claimed: dict, state: MockRoundState, *, user_id: str,
                             session_id: str, now_ms: int | None = None) -> dict | None:
        deadline = self._question_deadline(claimed, state)
        now_ms = self.now_ms() if now_ms is None else now_ms
        if deadline is None or now_ms < deadline:
            return None
        return await asyncio.to_thread(self.repository.expire_duration,
            user_id=user_id, session_id=session_id, now_ms=now_ms)

    def _question_deadline(self, record: dict, state: MockRoundState) -> int | None:
        deadline_method = getattr(self.repository, "duration_deadline", None)
        return deadline_method(record) if state.phase == "generating_question" and callable(deadline_method) else None

    @classmethod
    def _expired_question(cls, state: MockRoundState, record: dict) -> bool:
        return cls._duration_ended_question(state, record) and round_state(record).phase == "generating_report"

    @staticmethod
    def _duration_ended_question(state: MockRoundState, record: dict) -> bool:
        current = round_state(record)
        return (state.phase == "generating_question" and current.phase in ("generating_report", "completed")
                and current.operation_id != state.operation_id and record["data"].get("end_reason") == "time_limit")

    async def _run_claimed(self, claimed: dict, state: MockRoundState, *, user_id: str, session_id: str) -> dict:
        finish = dict(user_id=user_id, session_id=session_id, operation_id=state.operation_id, claim_id=claimed['data']['generation_claim'])
        provider_attempted = False
        deadline = self._question_deadline(claimed, state)
        timeout_seconds = self.repository.settings.mock_interview_provider_timeout_seconds
        duration_timeout = False
        if deadline is not None:
            remaining_seconds = max(0, deadline - self.now_ms()) / 1000
            duration_timeout = remaining_seconds <= timeout_seconds
            timeout_seconds = min(timeout_seconds, remaining_seconds)
        timeout = asyncio.timeout_at(monotonic() + timeout_seconds)
        diagnostics = MockGenerationDiagnostics(self.repository.settings,
            "question" if state.phase == "generating_question" else "report")
        token = diagnostics.activate()
        total_started = monotonic()
        total_outcome, total_error = "success", None
        try:
            expired = await self._expire_if_due(claimed, state, user_id=user_id, session_id=session_id)
            if expired is not None:
                total_outcome = "cancelled"
                return expired
            async with timeout:
                data = claimed['data']
                if state.phase == 'generating_report' and (not any((r.answer for r in state.rounds))):
                    resume = ''
                else:
                    if not data.get('resume_id') or not data.get('resume_version'):
                        total_error = "context_invalid"
                        raise ValueError('missing selected resume')
                    resume_started = monotonic()
                    resume_outcome, resume_error = "success", None
                    try:
                        resume = await asyncio.to_thread(self.reader.read, user_id=user_id, document_id=data['resume_id'], version_id=data['resume_version'])
                    except DomainRequestError:
                        resume_error = "resume_unavailable"
                        if state.phase != 'generating_report':
                            resume_outcome, total_error = "failed", "resume_unavailable"
                            raise
                        resume_outcome = "fallback"
                        resume = '[原简历版本已不可用，本报告仅依据已确认的问答。]'
                    except asyncio.CancelledError:
                        resume_outcome = "cancelled"
                        raise
                    except Exception:
                        resume_outcome, resume_error, total_error = "failed", "resume_unavailable", "resume_unavailable"
                        raise
                    finally:
                        diagnostics.record("resume_read", resume_started,
                            outcome=resume_outcome, error_category=resume_error)
                args = dict(resume=resume, target_role=data['target_role'], rounds=state.rounds)
                expired = await self._expire_if_due(claimed, state, user_id=user_id, session_id=session_id)
                if expired is not None:
                    total_outcome = "cancelled"
                    return expired
                provider_attempted = True
                if state.phase == 'generating_question':
                    result = await self.generator.question(**args)
                    output = {'question': result.question}
                else:
                    result = await self.generator.report(**args)
                    output = {'report': result.model_dump()}
            result = await asyncio.to_thread(self.repository.finish_generation, **finish, now_ms=self.now_ms(), **output)
            if self._duration_ended_question(state, result):
                total_outcome = "cancelled"
            return result
        except asyncio.CancelledError:
            total_outcome = "cancelled"
            await asyncio.shield(self._release_cancelled(finish, claimed, state))
            raise
        except Exception as exc:
            # Recovery I/O may fail too. Mark the operation failed before any
            # recovery await so its final diagnostic cannot claim success.
            total_outcome = "failed"
            if total_error is None:
                if isinstance(exc, MockGenerationUnavailable):
                    total_error = exc.error_category
                elif isinstance(exc, TimeoutError):
                    total_error = "generation_timeout"
                elif isinstance(exc, DomainRequestError):
                    total_error = "commit_rejected"
                else:
                    total_error = "internal_error"
            expiry_time = self.now_ms()
            if duration_timeout and isinstance(exc, TimeoutError) and timeout.expired():
                expiry_time = max(expiry_time, deadline)
            expired = await self._expire_if_due(claimed, state, user_id=user_id, session_id=session_id, now_ms=expiry_time)
            if expired is not None:
                total_outcome, total_error = "cancelled", None
                return expired
            provider_fault = isinstance(exc, MockGenerationUnavailable) or (provider_attempted and isinstance(exc, TimeoutError)) or (isinstance(exc, DomainRequestError) and exc.error_code in ('mock_repeated_question', 'mock_invalid_question'))
            await self._release_failed(finish, provider_fault=provider_fault)
            return await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)
        finally:
            diagnostics.record("generation_total", total_started,
                outcome=total_outcome, error_category=total_error)
            diagnostics.reset(token)
