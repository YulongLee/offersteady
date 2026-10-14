"""Synthetic failures only: never call a provider or load production data."""
import asyncio
import json
import logging
from dataclasses import asdict
from time import monotonic
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import LOGGER_NAME
from app.schemas.mock_interview import MockReport
from app.services.mock_interview_diagnostics import MockGenerationDiagnostics
from app.services.mock_interview_generation import MockGenerationUnavailable, MockInterviewGenerator
from app.services.mock_interview_jobs import MockInterviewJobs
from app.services.mock_interview_rounds import MockRound, MockRoundState


PRIVATE = "SYNTHETIC_PRIVATE_CONTENT_9a21"


def settings(**changes):
    return Settings(_env_file=None, chat_qwen_api_key=PRIVATE,
                    chat_qwen_base_url=f"https://synthetic.invalid/{PRIVATE}", **changes)


def response(content=None, *, finish="stop", status=200):
    return httpx.Response(status, json={"choices": [{"finish_reason": finish,
        "message": {"content": json.dumps(content or {"question": "如何验证结果？", "focus": "测试"}, ensure_ascii=False)}}]})


@pytest.fixture
def diagnostic_events(caplog, monkeypatch):
    monkeypatch.setattr(logging.getLogger(LOGGER_NAME), "propagate", True)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    def read():
        captured = [json.loads(record.message) for record in caplog.records
                    if record.name == LOGGER_NAME and "mock_interview.generation_stage" in record.message]
        assert PRIVATE not in json.dumps(captured)
        for event in captured:
            assert set(event) <= {"timestamp", "level", "service", "environment", "event", "feature", "action",
                                 "kind", "diagnostic_id", "stage", "outcome", "duration_ms", "error_code", "http_status"}
            assert event["duration_ms"] >= 0
            assert len(event["diagnostic_id"]) == 32
        return captured
    return read


@pytest.mark.parametrize("case,category,stage", [
    ("http", "provider_http_error", "provider_request"),
    ("http_timeout", "provider_timeout", "provider_request"),
    ("transport", "provider_transport_error", "provider_request"),
    ("outer_json", "response_json_invalid", "response_parse"),
    ("envelope", "response_envelope_invalid", "response_parse"),
    ("empty_choices", "response_envelope_invalid", "response_parse"),
    ("finish", "incomplete_response", "response_parse"),
    ("model_json", "response_json_invalid", "response_parse"),
    ("not_object", "structured_output_invalid", "response_parse"),
    ("oversized", "response_too_large", "response_parse"),
    ("schema", "question_schema_invalid", "output_validation"),
    ("duplicate", "repeated_question", "output_validation"),
])
def test_safe_failure_classification_preserves_single_call(case, category, stage, diagnostic_events):
    calls = []
    def handle(request):
        calls.append(request)
        if case == "http": return httpx.Response(429, text=PRIVATE)
        if case == "http_timeout": raise httpx.ReadTimeout(PRIVATE, request=request)
        if case == "transport": raise httpx.ConnectError(PRIVATE, request=request)
        if case == "outer_json": return httpx.Response(200, text=PRIVATE)
        if case == "envelope": return httpx.Response(200, json={"error": PRIVATE})
        if case == "empty_choices": return httpx.Response(200, json={"choices": []})
        if case == "finish": return response(finish="length")
        if case == "model_json": return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": PRIVATE}}]})
        if case == "not_object": return response([PRIVATE])
        if case == "oversized": return httpx.Response(200, text=PRIVATE + "x" * (128 * 1024))
        if case == "schema": return response({"question": "", "focus": PRIVATE})
        return response({"question": PRIVATE + "？", "focus": "合成"})
    service = MockInterviewGenerator(settings(), transport=httpx.MockTransport(handle))
    rounds = (MockRound(PRIVATE, PRIVATE + "？", PRIVATE),)
    with pytest.raises(MockGenerationUnavailable) as caught:
        asyncio.run(service.question(resume=PRIVATE, target_role=PRIVATE, rounds=rounds))
    assert caught.value.error_category == category
    assert len(calls) == 1
    events = diagnostic_events()
    failed = [event for event in events if event["outcome"] == "failed"]
    assert len(failed) == 1
    assert (failed[0]["stage"], failed[0]["error_code"]) == (stage, category)
    assert failed[0].get("http_status") == (429 if case == "http" else None)
    assert len({event["diagnostic_id"] for event in events}) == 1


def test_success_timings_and_trace_are_fixed_and_reset_between_generations(diagnostic_events):
    service = MockInterviewGenerator(settings(), transport=httpx.MockTransport(lambda _: response()))
    for _ in range(2):
        result = asyncio.run(service.question(resume=PRIVATE, target_role=PRIVATE, rounds=()))
        assert result.question == "如何验证结果？"
    events = diagnostic_events()
    stages = ["context_validation", "slot_wait", "provider_request", "response_parse", "output_validation"]
    assert [event["stage"] for event in events] == stages * 2
    assert all(event["outcome"] == "success" for event in events)
    assert len({event["diagnostic_id"] for event in events[:5]}) == 1
    assert len({event["diagnostic_id"] for event in events}) == 2


@pytest.mark.parametrize("malformed,category", [(True, "report_schema_invalid"), (False, "report_evidence_invalid")])
def test_report_schema_and_evidence_failures_are_safe_and_distinct(malformed, category, diagnostic_events):
    payload = {"summary": PRIVATE, "dimensions": {"relevance": 80, "clarity": 70, "depth": 60, "evidence": 50},
               "feedback": [{"question_id": "synthetic-q1", "answer_quote": "unsubmitted-evidence",
                             "strength": PRIVATE, "improvement": PRIVATE, "suggestion": PRIVATE}],
               "practice_priorities": [PRIVATE]}
    if malformed:
        payload["dimensions"]["evidence"] = 999
    calls = []
    def handle(request):
        calls.append(request)
        return response(payload)
    service = MockInterviewGenerator(settings(), transport=httpx.MockTransport(handle))
    with pytest.raises(MockGenerationUnavailable) as caught:
        asyncio.run(service.report(resume=PRIVATE, target_role=PRIVATE,
                                  rounds=(MockRound("synthetic-q1", PRIVATE, PRIVATE),)))
    assert caught.value.error_category == category and len(calls) == 1
    assert diagnostic_events()[-1]["error_code"] == category


@pytest.mark.parametrize("stage", ["slot_wait", "provider_request"])
def test_generation_deadline_distinguishes_queue_from_provider(stage, diagnostic_events):
    calls = []
    async def handle(request):
        calls.append(request)
        await asyncio.Event().wait()
    service = MockInterviewGenerator(settings(mock_interview_provider_timeout_seconds=1),
                                     transport=httpx.MockTransport(handle))
    async def scenario():
        if stage == "slot_wait":
            for _ in range(service.settings.mock_interview_provider_concurrency):
                await service._slots.acquire()
        with pytest.raises(MockGenerationUnavailable) as caught:
            await service.question(resume=PRIVATE, target_role="", rounds=())
        assert caught.value.error_category == ("slot_wait_timeout" if stage == "slot_wait" else "provider_timeout")
        if stage == "slot_wait":
            for _ in range(service.settings.mock_interview_provider_concurrency):
                service._slots.release()
    asyncio.run(scenario())
    events = diagnostic_events()
    assert events[-1]["stage"] == stage and events[-1]["outcome"] == "failed"
    assert len(calls) == (0 if stage == "slot_wait" else 1)


def fake_job(*, generator, reader=None, cfg=None, report=False):
    state = MockRoundState().start()
    if report:
        state = state.publish_question(state.operation_id, "合成问题？")
        state = state.listen(state.rounds[-1].question_id, 1)
        state = state.submit(question_id=state.rounds[-1].question_id, answer=PRIVATE, submission_id="synthetic")
        state = state.end()
    record = {"session_id": "synthetic-session", "data": {"state": asdict(state), "generation_claim": "synthetic-claim",
              "resume_id": "synthetic-resume", "resume_version": "synthetic-v1", "target_role": PRIVATE}}
    repo = SimpleNamespace(settings=cfg or settings(), get=Mock(return_value=record),
                           claim_generation=Mock(return_value=record), finish_generation=Mock(return_value=record))
    reader = reader or SimpleNamespace(read=Mock(return_value=PRIVATE))
    return MockInterviewJobs(repo, reader, generator), repo, record


@pytest.mark.parametrize("error,provider_fault,category", [
    (MockGenerationUnavailable(PRIVATE, error_category="response_json_invalid"), True, "response_json_invalid"),
    (RuntimeError(PRIVATE), False, "internal_error"),
    (DomainRequestError("mock-interview", "generate", PRIVATE, error_code="mock_repeated_question"), True, "commit_rejected"),
])
def test_job_failure_accounting_and_release_are_unchanged(error, provider_fault, category, diagnostic_events):
    generator = SimpleNamespace(question=AsyncMock(side_effect=error))
    jobs, repo, record = fake_job(generator=generator)
    assert asyncio.run(jobs.run_pending(user_id="synthetic-owner", session_id="synthetic-session")) is record
    assert generator.question.await_count == 1
    assert repo.finish_generation.call_args.kwargs["failed"] is True
    assert repo.finish_generation.call_args.kwargs["provider_fault"] is provider_fault
    assert [event["stage"] for event in diagnostic_events()] == ["resume_read", "generation_total"]
    assert diagnostic_events()[-1]["error_code"] == category


def test_resume_failure_is_not_a_provider_fault_and_never_calls_model(diagnostic_events):
    reader = SimpleNamespace(read=Mock(side_effect=DomainRequestError("mock-interview", "resume", PRIVATE)))
    generator = SimpleNamespace(question=AsyncMock())
    jobs, repo, _ = fake_job(generator=generator, reader=reader)
    asyncio.run(jobs.run_pending(user_id="synthetic-owner", session_id="synthetic-session"))
    generator.question.assert_not_awaited()
    assert repo.finish_generation.call_args.kwargs["provider_fault"] is False
    events = diagnostic_events()
    assert all(event["error_code"] == "resume_unavailable" for event in events)


def test_report_resume_fallback_remains_available_without_disclosing_reason(diagnostic_events):
    reader = SimpleNamespace(read=Mock(side_effect=DomainRequestError("mock-interview", "resume", PRIVATE)))
    generator = SimpleNamespace(report=AsyncMock(return_value=MockReport(summary="合成报告")))
    jobs, repo, _ = fake_job(generator=generator, reader=reader, report=True)
    asyncio.run(jobs.run_pending(user_id="synthetic-owner", session_id="synthetic-session"))
    generator.report.assert_awaited_once()
    assert "failed" not in repo.finish_generation.call_args.kwargs
    events = diagnostic_events()
    assert events[0]["outcome"] == "fallback" and events[-1]["outcome"] == "success"


def test_outer_job_deadline_releases_claim_and_logs_total_timeout(diagnostic_events):
    calls = []
    async def handle(request):
        calls.append(request)
        await asyncio.Event().wait()
    cfg = settings(mock_interview_provider_timeout_seconds=1)
    generator = MockInterviewGenerator(cfg, transport=httpx.MockTransport(handle))
    jobs, repo, _ = fake_job(generator=generator, cfg=cfg)
    asyncio.run(jobs.run_pending(user_id="synthetic-owner", session_id="synthetic-session"))
    assert repo.finish_generation.call_args.kwargs["provider_fault"] is True
    assert len(calls) == 1
    events = diagnostic_events()
    assert events[-2]["stage"] == "provider_request" and events[-2]["outcome"] == "cancelled"
    assert events[-1]["error_code"] == "generation_timeout"


def test_cancelled_job_releases_claim_without_provider_failure(diagnostic_events):
    async def scenario():
        entered = asyncio.Event()
        async def question(**_):
            entered.set()
            await asyncio.Event().wait()
        jobs, repo, _ = fake_job(generator=SimpleNamespace(question=question))
        task = asyncio.create_task(jobs.run_pending(user_id="synthetic-owner", session_id="synthetic-session"))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        assert repo.finish_generation.call_args.kwargs["failed"] is True
        assert repo.finish_generation.call_args.kwargs["provider_fault"] is False
    asyncio.run(scenario())
    assert diagnostic_events()[-1]["outcome"] == "cancelled"


def test_concurrent_generations_have_distinct_traces_and_cancellation_stays_cancellation(diagnostic_events):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        requests = []
        async def handle(request):
            requests.append(request)
            if len(requests) == 2: entered.set()
            await release.wait()
            return response()
        service = MockInterviewGenerator(settings(), transport=httpx.MockTransport(handle))
        one = asyncio.create_task(service.question(resume=PRIVATE, target_role="", rounds=()))
        two = asyncio.create_task(service.question(resume=PRIVATE, target_role="", rounds=()))
        await asyncio.wait_for(entered.wait(), 1)
        one.cancel()
        with pytest.raises(asyncio.CancelledError): await one
        release.set()
        assert (await two).question == "如何验证结果？"
        assert service._slots._value == service.settings.mock_interview_provider_concurrency
    asyncio.run(scenario())
    events = diagnostic_events()
    assert len({event["diagnostic_id"] for event in events}) == 2
    cancelled = [event for event in events if event["outcome"] == "cancelled"]
    assert len(cancelled) == 1 and cancelled[0]["stage"] == "provider_request"


def test_job_and_provider_share_only_random_trace(diagnostic_events):
    generator = MockInterviewGenerator(settings(), transport=httpx.MockTransport(lambda _: response()))
    jobs, _, _ = fake_job(generator=generator)
    asyncio.run(jobs.run_pending(user_id="synthetic-owner", session_id="synthetic-session"))
    events = diagnostic_events()
    assert len({event["diagnostic_id"] for event in events}) == 1
    assert [event["stage"] for event in events] == ["resume_read", "context_validation", "slot_wait", "provider_request",
                                                  "response_parse", "output_validation", "generation_total"]


def test_unknown_diagnostic_fields_cannot_echo_sensitive_values(diagnostic_events):
    diagnostics = MockGenerationDiagnostics(settings(), PRIVATE)
    diagnostics.record(PRIVATE, monotonic(), error_category=PRIVATE)
    diagnostics.record("resume_read", monotonic(), outcome=PRIVATE, error_category=PRIVATE, http_status=999)
    events = diagnostic_events()
    assert len(events) == 1
    assert events[0]["kind"] == "unknown" and events[0]["error_code"] == "internal_error"
    assert "http_status" not in events[0]
