"""Global practice regressions with synthetic PG records and blocked fake ASR."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.errors import DomainRequestError
from app.ports.realtime_speech import TranscriptResult
from app.schemas.mock_interview import MockQuestion, MockReport
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_jobs import MockInterviewJobs
from app.services.mock_interview_repository import round_state
from app.services.mock_interview_runtime import MockInterviewRuntime
from app.services.realtime_speech_service import RealtimeSpeechService
from test_global_mock_postgres import NOW, URL, create, member, repos


pytestmark = pytest.mark.skipif(not URL, reason="Disposable Global practice DB required")


async def listening_global(repos):
    repository, commerce, _ = repos
    user, _ = member(commerce)
    now = [NOW]
    row = create(repository, user, "synthetic-turn-cleanup")
    sid = row["session_id"]
    repository.select_resume(user_id=user, session_id=sid, expected_version=0,
        document_id="synthetic-global-resume", version_id="synthetic-v1", now_ms=now[0])
    reader = Mock()
    reader.read.return_value = "Synthetic backend engineer. Validated idempotent operations."
    generator = SimpleNamespace(
        question=AsyncMock(return_value=MockQuestion(question="How did you validate an idempotent API?", focus="Reliability")),
        report=AsyncMock(return_value=MockReport(summary="Synthetic English practice report.")))
    gateways = []
    def factory():
        gateway = Mock()
        gateway.transcribe.return_value = TranscriptResult("Synthetic confirmed answer.", .9)
        gateways.append(gateway)
        return gateway
    audio = MockInterviewAudio(gateway_factory=factory, now_ms=lambda: now[0])
    jobs = MockInterviewJobs(repository, reader, generator, now_ms=lambda: now[0])
    realtime = Mock()
    realtime.session_service.get_session.return_value = SimpleNamespace(status="live", session_mode="mock")
    realtime.get_desktop_binding.return_value = SimpleNamespace(device_id="synthetic-device", binding_generation=1,
        status="bound", manual_code="000000")
    realtime.repository.get_desktop_device_by_code.return_value = SimpleNamespace(device_id="synthetic-device", generation=1,
        capabilities={"mockInterviewProtocol": 1, "microphone": "granted"})
    realtime._desktop_device_fresh.return_value = True
    realtime._permission_status.side_effect = RealtimeSpeechService._permission_status
    runtime = MockInterviewRuntime(repository, reader, jobs, Mock(), audio, realtime, now_ms=lambda: now[0])
    messages = []
    async def send(message):
        messages.append(message)
    controller = await runtime.attach(user_id=user, session_id=sid, send=send)
    runtime.desktops[sid] = ("synthetic-device", AsyncMock())
    await runtime.command(controller, action="start", version=round_state(controller.record).version)
    await controller.generation
    state = round_state(controller.record)
    await runtime.command(controller, action="listen", version=state.version, question_id=state.rounds[-1].question_id)
    return runtime, controller, now, generator, gateways, messages


def test_global_submit_does_not_wait_for_old_asr_or_use_domestic_billing(repos):
    async def run():
        asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1))
        runtime, controller, now, generator, gateways, messages = await listening_global(repos)
        closing, release = Event(), Event()
        def slow_close(**kwargs):
            closing.set()
            assert release.wait(5), "Synthetic ASR close must be released"
        gateways[0].close_session.side_effect = slow_close
        state = round_state(controller.record)
        old = runtime.audio._captures[controller.session_id]
        generator.question.return_value = MockQuestion(question="How did you test concurrent requests?", focus="Concurrency")
        submission = dict(action="submit", version=state.version, question_id=state.rounds[-1].question_id,
            answer="I used synthetic unique request keys and checked a single durable write.", submission_id="synthetic-submit")
        try:
            now[0] += 1000
            await asyncio.wait_for(runtime.command(controller, **submission), 2)
            assert await asyncio.to_thread(closing.wait, 2)
            await asyncio.wait_for(controller.generation, 2)
            assert old.revoked and not old.closed
            assert len(round_state(controller.record).rounds) == 2
            assert any(m.get("session", {}).get("state", {}).get("phase") == "generating_question" for m in messages)
            assert controller.record["data"]["clock_at_ms"] is None
            assert controller.record["data"]["billed_minutes"] == 0
            assert runtime.repository.quote(controller.user_id, now[0])["dailyFreeRemaining"] == 2
            await runtime.command(controller, **submission)
            assert generator.question.await_count == 2
            with pytest.raises(DomainRequestError):
                runtime.audio.ingest(session_id=controller.session_id, device_id="synthetic-device", epoch=old.epoch, pcm=b"00")
        finally:
            release.set()
            await runtime.shutdown()
        assert old.closed and not runtime.audio._closing and not runtime._capture_closes
        assert gateways[0].close_session.call_count == 1
    asyncio.run(run())


def test_global_next_round_isolated_from_late_old_transcript(repos):
    async def run():
        runtime, controller, _, generator, gateways, messages = await listening_global(repos)
        sid = controller.session_id
        old = runtime.audio._captures[sid]
        closing, release = Event(), Event()
        def slow_close(**kwargs):
            closing.set()
            assert release.wait(5), "Synthetic ASR close must be released"
        gateways[0].close_session.side_effect = slow_close
        try:
            await asyncio.to_thread(runtime.audio.ingest, session_id=sid, device_id="synthetic-device", epoch=old.epoch, pcm=b"00")
            old_frame = gateways[0].transcribe.call_args.kwargs["frame"]
            state = round_state(controller.record)
            generator.question.return_value = MockQuestion(question="What did the synthetic validation prove?", focus="Validation")
            await runtime.command(controller, action="submit", version=state.version, question_id=state.rounds[-1].question_id,
                answer="The synthetic trace proved one confirmed request was committed.", submission_id="synthetic-submit")
            assert await asyncio.to_thread(closing.wait, 2)
            await controller.generation
            state = round_state(controller.record)
            await asyncio.wait_for(runtime.command(controller, action="listen", version=state.version, question_id=state.rounds[-1].question_id), 2)
            new = runtime.audio._captures[sid]
            assert new.epoch != old.epoch and new.gateway is not old.gateway
            gateways[1].transcribe.return_value = TranscriptResult("Synthetic new-round answer.", .9)
            runtime.audio._partial(old_frame, TranscriptResult("Synthetic late answer must be discarded.", .9))
            runtime._draft(controller, old.epoch, "Synthetic late queued draft.")
            await asyncio.to_thread(runtime.audio.ingest, session_id=sid, device_id="synthetic-device", epoch=new.epoch, pcm=b"00")
            await asyncio.sleep(0)
            await runtime.flush_draft(controller)
            assert messages[-1] == {"type": "transcript", "epoch": new.epoch, "text": "Synthetic new-round answer."}
            release.set()
            await runtime._drain_capture_closes(controller.capture_closes)
            assert runtime.audio._captures[sid] is new and not new.closed
            gateways[1].close_session.assert_not_called()
        finally:
            release.set()
            await runtime.shutdown()
        assert not runtime.audio._closing and not runtime._capture_closes
    asyncio.run(run())


def test_global_practice_preserves_no_sixty_minute_deadline(repos):
    repository, commerce, _ = repos
    user, _ = member(commerce)
    row = create(repository, user, "synthetic-long-practice")
    sid = row["session_id"]
    row = repository.transition(user_id=user, session_id=sid, expected_version=0, now_ms=NOW, move=lambda state: state.start())
    state = round_state(row)
    claim = repository.claim_generation(user_id=user, session_id=sid, operation_id=state.operation_id, now_ms=NOW)
    row = repository.finish_generation(user_id=user, session_id=sid, operation_id=state.operation_id,
        claim_id=claim["data"]["generation_claim"], now_ms=NOW, question="How did you validate the synthetic example?")
    row = repository.acquire_control(user_id=user, session_id=sid, now_ms=NOW)
    for offset in range(0, 3_720_001, 10_000):
        row = repository.control_tick(user_id=user, session_id=sid, control_token=row["data"]["control_token"],
            now_ms=NOW+offset, active=True)
    assert round_state(row).phase == "speaking"
    assert not row["data"].get("deadline_at_ms") and not row["data"].get("end_reason")
    assert row["data"]["billable_ms"] == 3_720_000 and row["data"]["billed_minutes"] == 0
    quote = repository.quote(user, NOW+3_720_000)
    assert quote["dailyFreeRemaining"] == 2 and quote["dailyLimit"] == 3 and quote["timezone"] == "UTC"
