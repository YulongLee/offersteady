"""Bounded text jobs with durable claims, no database lock across provider I/O.

Start/capture require the dedicated billing and desktop lifecycle. This
coordinator cannot create, start or charge a session.
"""
from __future__ import annotations

import asyncio
from time import time

from app.core.errors import DomainRequestError
from app.services.mock_interview_generation import MockInterviewGenerator, MockResumeReader, MockGenerationUnavailable
from app.services.mock_interview_repository import MockInterviewRepository, round_state


class MockInterviewJobs:
    def __init__(self, repository: MockInterviewRepository, reader: MockResumeReader,
                 generator: MockInterviewGenerator, *, now_ms=None):
        self.repository = repository
        self.reader = reader
        self.generator = generator
        self.now_ms = now_ms or (lambda: int(time() * 1000))

    async def run_pending(self, *, user_id: str, session_id: str) -> dict:
        record = await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)
        state = round_state(record)
        if state.phase not in ("generating_question", "generating_report"):
            return record
        claimed = await asyncio.to_thread(self.repository.claim_generation, user_id=user_id,
            session_id=session_id, operation_id=state.operation_id, now_ms=self.now_ms())
        finish = dict(user_id=user_id, session_id=session_id, operation_id=state.operation_id,
                      claim_id=claimed["data"]["generation_claim"])
        provider_attempted = False
        try:
            async with asyncio.timeout(self.repository.settings.mock_interview_provider_timeout_seconds):
                data = claimed["data"]
                # Ending preparation needs neither a selected resume nor a paid
                # model call; the generator returns an unscored evidence state.
                if state.phase == "generating_report" and not any(r.answer for r in state.rounds):
                    resume = ""
                else:
                    if not data.get("resume_id") or not data.get("resume_version"):
                        raise ValueError("missing selected resume")
                    try:
                        resume = await asyncio.to_thread(self.reader.read, user_id=user_id,
                            document_id=data["resume_id"], version_id=data["resume_version"])
                    except DomainRequestError:
                        if state.phase != "generating_report":
                            raise
                        # Deleted/changed resume cannot prevent a report of
                        # already submitted answers. Never revive deleted data.
                        resume = "[原简历版本已不可用，本报告仅依据已确认的问答。]"
                args = dict(resume=resume, target_role=data["target_role"], rounds=state.rounds)
                provider_attempted = True
                if state.phase == "generating_question":
                    result = await self.generator.question(**args)
                    output = {"question": result.question}
                else:
                    result = await self.generator.report(**args)
                    output = {"report": result.model_dump()}
            return await asyncio.to_thread(self.repository.finish_generation, **finish,
                now_ms=self.now_ms(), **output)
        except asyncio.CancelledError:
            # A disconnected HTTP caller cannot leave the next attempt locked
            # until restart. A bounded durable lease also covers process death.
            await asyncio.shield(self._release_failed(finish))
            raise
        except Exception as exc:
            # Do not persist provider messages, keys or resume contents.
            provider_fault = (isinstance(exc, MockGenerationUnavailable)
                or provider_attempted and isinstance(exc, TimeoutError)
                or isinstance(exc, DomainRequestError) and exc.error_code in ("mock_repeated_question", "mock_invalid_question"))
            await self._release_failed(finish, provider_fault=provider_fault)
            return await asyncio.to_thread(self.repository.get, user_id=user_id, session_id=session_id)

    async def _release_failed(self, finish: dict, *, provider_fault: bool = False) -> None:
        try:
            await asyncio.to_thread(self.repository.finish_generation, **finish,
                now_ms=self.now_ms(), failed=True, provider_fault=provider_fault)
        except DomainRequestError as exc:
            if exc.error_code not in ("mock_stale_operation", "mock_session_ended", "mock_not_found"):
                raise
