from __future__ import annotations

import base64
import logging
import threading
from pathlib import Path
from time import monotonic, perf_counter, sleep, time

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.realtime_speech import should_validate_realtime_session
from app.deps import realtime_speech_service
from app.ports.authentication import SmsChallengeRecord
from app.ports.realtime_speech import AudioFrame, RealtimeEvent, TranscriptResult
from app.ports.chat import ChatAnswerChunk, PromptBuildResult, PromptConfig
from app.ports.retrieval import RetrievalContext
from app.services.chat_service import NonRetryableChatError, QwenCompatibleGateway, RetryableChatError
from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.sms_verification_provider import AliyunDypnsSmsVerificationProvider, AliyunDysmsSmsVerificationProvider


def test_realtime_stream_throttles_database_backed_session_validation() -> None:
    assert should_validate_realtime_session(last_validated_at=10.0, now=24.999) is False
    assert should_validate_realtime_session(last_validated_at=10.0, now=25.0) is True


def test_realtime_stream_bootstrap_is_bounded_to_latest_stateful_events() -> None:
    user_id = "bounded-bootstrap-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "有界首屏测试"}))
    session_id = session["sessionId"]
    service = realtime_speech_service()
    service.publish_session_event(
        user_id=user_id,
        session_id=session_id,
        kind="degraded",
        payload={"reason": "older-state"},
    )
    service.publish_session_event(
        user_id=user_id,
        session_id=session_id,
        kind="transcript-updated",
        payload={"segmentId": "separate-authoritative-transcript", "revision": 1},
    )
    service.publish_session_event(
        user_id=user_id,
        session_id=session_id,
        kind="degraded",
        payload={"reason": "latest-state"},
    )
    service.publish_session_event(
        user_id=user_id,
        session_id=session_id,
        kind="capture-control",
        payload={"captureState": "capturing"},
    )

    bootstrap = service.list_stream_bootstrap_events(user_id=user_id, session_id=session_id)
    events = bootstrap.model_dump(by_alias=True)["events"]

    assert {item["kind"] for item in events} == {"degraded", "capture-control"}
    degraded = next(item for item in events if item["kind"] == "degraded")
    assert degraded["payload"]["reason"] == "latest-state"
    assert all(item["kind"] != "transcript-updated" for item in events)


def test_realtime_session_snapshot_is_authorized_complete_and_lease_aware() -> None:
    user_id = "snapshot-owner-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "恢复快照测试"}))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    lease = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": user_id,
        "bindingId": None,
        "page": "live",
        "pageInstanceId": "snapshot-page-1",
    }))

    response = client.get(f"/api/v1/realtime-speech/sessions/{session_id}/snapshot", params={
        "userId": user_id,
        "pageInstanceId": lease["pageInstanceId"],
        "leaseGeneration": lease["leaseGeneration"],
    })
    assert response.status_code == 200
    snapshot = unwrap(response)
    assert snapshot["sessionId"] == session_id
    assert snapshot["ownerUserId"] == user_id
    assert snapshot["runtime"]["sessionId"] == session_id
    assert snapshot["transcripts"] == {"sessionId": session_id, "transcripts": []}
    assert snapshot["candidates"] == {"sessionId": session_id, "candidates": []}
    assert snapshot["events"]["sessionId"] == session_id
    assert isinstance(snapshot["cursor"], int)

    wrong_owner = client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/snapshot",
        params={"userId": "snapshot-other-user"},
    )
    assert wrong_owner.status_code == 403

    replacement = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "替代页面测试"}))
    replacement_id = replacement["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{replacement_id}/start", json={"userId": user_id}))
    replacement_lease = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{replacement_id}/web-heartbeat", json={
        "userId": user_id,
        "bindingId": None,
        "page": "live",
        "pageInstanceId": "snapshot-page-2",
    }))
    stale_lease = client.get(f"/api/v1/realtime-speech/sessions/{session_id}/snapshot", params={
        "userId": user_id,
        "pageInstanceId": "snapshot-page-1",
        "leaseGeneration": replacement_lease["leaseGeneration"],
    })
    assert stale_lease.status_code == 409

    unwrap(client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": user_id}))
    terminal = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/snapshot",
        params={"userId": user_id},
    ))
    assert terminal["runtime"]["sessionStatus"] == "ended"

    legacy = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/transcripts",
        params={"userId": user_id},
    ))
    assert legacy == terminal["transcripts"]


def test_runtime_performance_ack_accepts_only_allowlisted_metadata() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "performance-ack-user", "title": "性能确认测试",
    }))
    session_id = session["sessionId"]
    accepted = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/performance-ack", json={
        "userId": "performance-ack-user",
        "traceId": "trace-safe-1",
        "stage": "transcript-render",
        "durationMs": 42,
        "taskId": "task-safe-1",
    })
    assert accepted.status_code == 200
    events = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/events",
        params={"userId": "performance-ack-user"},
    ))["events"]
    # Rendering acknowledgements are metrics and must not be echoed into the
    # product event stream, otherwise every rendered transcript amplifies SSE.
    assert events == []

    answer_accepted = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/performance-ack", json={
        "userId": "performance-ack-user",
        "traceId": "answer-task-safe-1",
        "stage": "answer-first-render",
        "durationMs": 731,
        "taskId": "answer-task-safe-1",
        "browserEventReceiveAtMs": 1_000,
        "browserRenderAtMs": 1_010,
        "serverAcceptedAtMs": 100,
        "providerRequestAtMs": 200,
        "providerFirstTokenAtMs": 900,
        "firstVisibleAtMs": 1_400,
        "sseYieldAtMs": 1_405,
        "renderedTextLength": 18,
    })
    assert answer_accepted.status_code == 200
    screenshot_accepted = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/performance-ack", json={
        "userId": "performance-ack-user",
        "traceId": "screenshot-request-safe-1",
        "stage": "screenshot-first-render",
        "durationMs": 2_341,
        "taskId": "screenshot-task-safe-1",
        "browserRenderAtMs": 2_341,
        "renderedTextLength": 12,
    })
    assert screenshot_accepted.status_code == 200
    answer_summary = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/performance-summary",
        params={"userId": "performance-ack-user"},
    ))
    assert answer_summary["distributions"]["answerAdmissionToProviderMs"]["p95"] == 100
    assert answer_summary["distributions"]["answerProviderToFirstTokenMs"]["p95"] == 700
    assert answer_summary["distributions"]["answerFirstTokenToVisibleMs"]["p95"] == 500
    assert answer_summary["distributions"]["answerVisibleToSseYieldMs"]["p95"] == 5
    assert answer_summary["distributions"]["answerAdmissionToSseYieldMs"]["p95"] == 1_305
    assert answer_summary["distributions"]["answerBrowserReceiveToRenderMs"]["p95"] == 10
    assert answer_summary["distributions"]["answerClickToRenderMs"]["p95"] == 731
    assert answer_summary["distributions"]["screenshotClickToRenderMs"] == {
        "count": 1, "p50": 2_341, "p95": 2_341, "p99": 2_341, "max": 2_341,
    }
    traces = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/performance-traces",
        params={"userId": "performance-ack-user"},
    ))
    answer_trace = next(item for item in traces if item["traceId"] == "answer-task-safe-1")
    assert answer_trace == {
        "traceId": "answer-task-safe-1",
        "sessionId": session_id,
        "taskId": "answer-task-safe-1",
        "telemetryStage": "answer-first-render",
        "browserEventReceiveAtMs": 1_000,
        "browserRenderAtMs": 1_010,
        "renderedTextLength": 18,
        "serverAcceptedAtMs": 100,
        "providerRequestAtMs": 200,
        "providerFirstTokenAtMs": 900,
        "firstVisibleAtMs": 1_400,
        "sseYieldAtMs": 1_405,
        "answerClickToRenderMs": 731,
    }
    assert not ({"question", "answer", "content", "text", "prompt"} & answer_trace.keys())

    rejected = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/performance-ack", json={
        "userId": "performance-ack-user", "traceId": "trace-safe-2",
        "stage": "transcript-render", "durationMs": 10,
        "content": "不允许上传转写或截图内容",
    })
    assert rejected.status_code == 422


def test_realtime_trace_summary_correlates_browser_delivery_without_content() -> None:
    user_id = "trace-summary-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "Trace 基线测试"}))
    session_id = session["sessionId"]
    service = realtime_speech_service()
    service._observe_trace(
        "trace-summary-1",
        sessionId=session_id,
        channel="system",
        sequence=7,
        revision=1,
        utteranceId="segment-safe-1",
        desktopVadConfirmAtMs=985,
        desktopAudioWorkletOutputAtMs=990,
        desktopRendererReceiveAtMs=992,
        desktopPcmConversionAtMs=994,
        desktopRingBufferWriteAtMs=996,
        desktopPublisherEnqueueAtMs=997,
        desktopPublisherFlushAtMs=1_008,
        backendWebsocketFrameReceivedAtMs=1_030,
        backendFrameValidationDoneAtMs=1_031,
        backendChannelRoutingDoneAtMs=1_033,
        asrSessionLockWaitStartAtMs=1_056,
        asrSessionLockAcquiredAtMs=1_058,
        qwenSendEnqueueAtMs=1_060,
        qwenWsSendStartAtMs=1_061,
        qwenWsSendCompleteAtMs=1_064,
        audioRms=0.125,
        speechStartAtMs=980,
        desktopAudioCaptureAtMs=1_000,
        desktopWsSendAtMs=1_010,
        backendWsReceiveAtMs=1_030,
        queueEnterAtMs=1_035,
        queueLeaveAtMs=1_055,
        qwenFirstAudioAppendAtMs=1_060,
        qwenAudioAppendAtMs=1_065,
        qwenPartialReceivedAtMs=1_200,
        transcriptEventCreatedAtMs=1_205,
        redisEventXaddCompleteAtMs=1_210,
        redisEventXaddAtMs=1_210,
        redisEventXreadAtMs=1_212,
        sseGeneratorYieldAtMs=1_215,
        sseEventSendAtMs=1_215,
    )
    accepted = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/performance-ack", json={
        "userId": user_id,
        "traceId": "trace-summary-1",
        "stage": "transcript-render",
        "durationMs": 25,
        "eventId": "rt-event-safe-1",
        "browserStreamChunkReceivedAtMs": 1_228,
        "browserEventParsedAtMs": 1_230,
        "browserEventReceiveAtMs": 1_230,
        "transcriptStoreUpdateStartAtMs": 1_232,
        "transcriptStoreUpdateCompleteAtMs": 1_234,
        "browserStateUpdateAtMs": 1_234,
        "reactRenderStartAtMs": 1_236,
        "reactCommitAtMs": 1_238,
        "browserPaintAtMs": 1_240,
        "browserRenderAtMs": 1_240,
        "renderedRevision": 1,
        "renderedTextLength": 12,
        "visibilityState": "visible",
    })
    assert accepted.status_code == 200
    summary = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/performance-summary",
        params={"userId": user_id},
    ))
    assert summary["traceCount"] == 1
    assert summary["distributions"]["networkMs"] == {
        "count": 1, "p50": 20, "p95": 20, "p99": 20, "max": 20,
    }
    assert summary["distributions"]["sseDeliveryMs"]["p95"] == 15
    assert summary["distributions"]["browserRenderMs"]["p95"] == 10
    assert summary["distributions"]["browserStateUpdateMs"]["p95"] == 4
    assert summary["distributions"]["browserStateToReactRenderMs"]["p95"] == 6
    assert summary["distributions"]["redisXaddToXreadMs"]["p95"] == 2
    assert summary["distributions"]["speechStartToBrowserFirstPartialMs"]["p95"] == 260
    assert summary["distributions"]["desktopEnqueueToFlushMs"]["p95"] == 11
    assert summary["distributions"]["backendAsrLockWaitMs"]["p95"] == 2
    assert summary["distributions"]["qwenPartialMs"]["p95"] == 140
    assert summary["distributions"]["qwenLatestAppendToPartialMs"]["p95"] == 135
    assert summary["revisionDiagnostics"]["stageCounts"] == {
        "qwen": 1,
        "event": 1,
        "redisXadd": 1,
        "redisXread": 1,
        "sse": 1,
        "browser": 1,
        "store": 1,
        "reactCommit": 1,
        "paint": 1,
    }
    traces = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/performance-traces",
        params={"userId": user_id, "limit": 4096},
    ))
    assert traces[0]["audioRms"] == 0.125
    assert traces[0]["visibilityState"] == "visible"
    assert summary["distributions"]["endToEndPartialMs"]["p95"] == 240
    assert "text" not in str(summary).lower()
    assert len(traces) == 1
    assert traces[0]["traceId"] == "trace-summary-1"
    assert traces[0]["eventId"] == "rt-event-safe-1"
    assert "text" not in traces[0]
    assert "partialText" not in traces[0]
    assert traces[0]["renderedTextLength"] == 12


def test_first_visible_latency_uses_only_earliest_utterance_revision() -> None:
    service = realtime_speech_service()
    session_id = "first-visible-synthetic-session"
    for revision, partial_at_ms, paint_at_ms in ((1, 1_200, 1_240), (2, 1_500, 1_800)):
        service._observe_trace(
            f"first-visible-trace-{revision}",
            sessionId=session_id,
            channel="system",
            utteranceId="synthetic-utterance",
            revision=revision,
            speechStartAtMs=980,
            qwenFirstAudioAppendAtMs=1_060,
            qwenPartialReceivedAtMs=partial_at_ms,
            browserRenderAtMs=paint_at_ms,
            browserPaintAtMs=paint_at_ms,
            visibilityState="visible",
        )

    summary = service.performance_summary(session_id=session_id)
    assert summary["distributions"]["qwenPartialMs"] == {
        "count": 1, "p50": 140, "p95": 140, "p99": 140, "max": 140,
    }
    assert summary["distributions"]["speechStartToBrowserFirstPartialMs"] == {
        "count": 1, "p50": 260, "p95": 260, "p99": 260, "max": 260,
    }


def test_terminal_summary_measures_from_last_meaningful_speech() -> None:
    service = realtime_speech_service()
    session_id = "last-meaningful-terminal-session"
    service._observe_trace(
        "last-meaningful-terminal-trace",
        sessionId=session_id,
        channel="system",
        utteranceId="bounded-system-turn",
        desktopLastMeaningfulSpeechAtMs=1_000,
        desktopTerminalEnqueueAtMs=1_350,
        manualCommitSentAtMs=1_520,
        qwenFinalReceivedAtMs=1_880,
        browserPaintAtMs=2_000,
    )

    summary = service.performance_summary(session_id=session_id)
    assert summary["distributions"]["lastMeaningfulSpeechToCommitMs"] == {
        "count": 1, "p50": 520, "p95": 520, "p99": 520, "max": 520,
    }
    assert summary["distributions"]["lastMeaningfulSpeechToFinalMs"] == {
        "count": 1, "p50": 880, "p95": 880, "p99": 880, "max": 880,
    }
    assert summary["distributions"]["lastMeaningfulSpeechToTerminalEnqueueMs"] == {
        "count": 1, "p50": 350, "p95": 350, "p99": 350, "max": 350,
    }
    assert summary["distributions"]["terminalEnqueueToProviderFinalMs"] == {
        "count": 1, "p50": 530, "p95": 530, "p99": 530, "max": 530,
    }
    assert summary["distributions"]["providerFinalToBrowserPaintMs"] == {
        "count": 1, "p50": 120, "p95": 120, "p99": 120, "max": 120,
    }


def test_start_summary_reports_warm_promotion_boundaries() -> None:
    service = realtime_speech_service()
    session_id = "warm-promotion-summary-session"
    service._observe_trace(
        "warm-promotion-trace",
        sessionId=session_id,
        channel="system",
        utteranceId="warm-first-turn",
        liveObservedAtMs=1_000,
        publisherConnectedAtMs=1_080,
        sourceReadyAtMs=1_100,
        sourceReadyMode="promoted",
        desktopWsSendAtMs=1_160,
    )

    summary = service.performance_summary(session_id=session_id)
    assert summary["distributions"]["liveToPublisherConnectedMs"]["p95"] == 80
    assert summary["distributions"]["publisherConnectedToSourceReadyMs"]["p95"] == 20
    assert summary["distributions"]["liveToFirstFrameSendMs"]["p95"] == 160


def test_transcript_delivery_ack_records_browser_receive_without_fake_render() -> None:
    user_id = "trace-delivery-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "字幕投递测试"}))
    session_id = session["sessionId"]
    service = realtime_speech_service()
    service._observe_trace("trace-delivery-1", sessionId=session_id, sseEventSendAtMs=2_000)

    accepted = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/performance-ack", json={
        "userId": user_id,
        "traceId": "trace-delivery-1",
        "stage": "transcript-delivery",
        "durationMs": 25,
        "eventId": "rt-event-delivery-1",
        "browserStreamChunkReceivedAtMs": 2_023,
        "browserEventParsedAtMs": 2_025,
        "browserEventReceiveAtMs": 2_025,
        "transcriptStoreUpdateStartAtMs": 2_028,
        "transcriptStoreUpdateCompleteAtMs": 2_030,
        "browserStateUpdateAtMs": 2_030,
        "visibilityState": "visible",
    })
    assert accepted.status_code == 200
    rendered = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/performance-ack", json={
        "userId": user_id,
        "traceId": "trace-delivery-1",
        "stage": "transcript-render",
        "durationMs": 15,
        "eventId": "rt-event-delivery-1",
        "reactRenderStartAtMs": 2_035,
        "reactCommitAtMs": 2_037,
        "browserPaintAtMs": 2_040,
        "browserRenderAtMs": 2_040,
        "visibilityState": "visible",
    })
    assert rendered.status_code == 200
    traces = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/performance-traces",
        params={"userId": user_id},
    ))
    assert traces[0]["browserEventReceiveAtMs"] == 2_025
    assert traces[0]["browserStateUpdateAtMs"] == 2_030
    assert traces[0]["transcriptStoreUpdateStartAtMs"] == 2_028
    assert traces[0]["transcriptStoreUpdateCompleteAtMs"] == 2_030
    assert traces[0]["browserRenderAtMs"] == 2_040


def test_realtime_delivery_metrics_accept_only_content_free_fields() -> None:
    user_id = "delivery-metric-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "交付指标测试"}))
    session_id = session["sessionId"]
    accepted = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/delivery-metrics", json={
        "userId": user_id,
        "kind": "first-snapshot",
        "durationMs": 86,
        "attempt": 1,
        "reason": "opened",
    })
    assert accepted.status_code == 200
    metrics = unwrap(client.get("/api/v1/realtime-speech/metrics"))
    assert metrics["delivery"]["counts"]["first-snapshot"] >= 1
    assert metrics["delivery"]["latestDurationMs"]["first-snapshot"] == 86

    timeout_metric = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/delivery-metrics", json={
        "userId": user_id,
        "kind": "reconnect",
        "durationMs": 2_000,
        "reason": "first-snapshot-timeout",
    })
    assert timeout_metric.status_code == 200

    rejected = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/delivery-metrics", json={
        "userId": user_id,
        "kind": "first-snapshot",
        "durationMs": 10,
        "answer": "不允许进入遥测的用户内容",
    })
    assert rejected.status_code == 422


def test_postgres_interview_schema_initialization_is_single_flight(monkeypatch) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository

    settings = get_settings().model_copy(update={"database_url": "postgresql://synthetic-single-flight"})
    calls: list[int] = []

    def synthetic_ensure_tables(_repository) -> None:
        calls.append(1)
        sleep(0.03)

    monkeypatch.setattr(PostgresInterviewSessionRepository, "_ensure_tables", synthetic_ensure_tables)
    with PostgresInterviewSessionRepository._schema_lock:
        PostgresInterviewSessionRepository._schema_ready_for.discard(str(settings.database_url))
    with ThreadPoolExecutor(max_workers=4) as executor:
        repositories = list(executor.map(lambda _index: PostgresInterviewSessionRepository(settings), range(4)))

    assert len(repositories) == 4
    assert len(calls) == 1


client = TestClient(create_app())


def prompt_fixture() -> PromptBuildResult:
    return PromptBuildResult(
        system_prompt="system",
        user_prompt="user",
        rendered_prompt="system\n\nuser",
        prompt_config=PromptConfig(template_id="test", version="v-test", max_history_entries=1),
        retrieval_excerpt_count=0,
    )


def unwrap(response):
    payload = response.json()
    assert "requestId" in payload
    assert "meta" in payload
    return payload["data"]


def parse_sse_events(text: str) -> list[dict]:
    events: list[dict] = []
    for frame in text.strip().split("\n\n"):
        data_lines = [line.removeprefix("data:").strip() for line in frame.splitlines() if line.startswith("data:")]
        if data_lines:
            import json

            events.append(json.loads("\n".join(data_lines)))
    return events


def wait_for_task_stage(document_id: str, user_id: str, expected_stage: str, timeout_seconds: float = 3.0):
    deadline = time() + timeout_seconds
    last_payload = None
    while time() < deadline:
        response = client.get(f"/api/v1/document-processing/documents/{document_id}", params={"userId": user_id})
        if response.status_code == 200:
            last_payload = unwrap(response)
            if last_payload["latestTask"]["currentStage"] == expected_stage:
                return last_payload
        sleep(0.05)
    assert last_payload is not None, f"Processing task for {document_id} did not become visible."
    assert last_payload["latestTask"]["currentStage"] == expected_stage, last_payload


def test_health_check() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = unwrap(response)
    assert payload["status"] == "ok"
    assert payload["service"] == "OfferSteady Backend"
    assert response.headers["X-Request-Id"]


def test_realtime_repository_tracks_session_activity_version() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    assert repository.get_session_activity_version(session_id="session-activity") == 0
    repository.save_event(RealtimeEvent(
        event_id="event-1",
        session_id="session-activity",
        owner_user_id="user-1",
        kind="degraded",
        payload={"reason": "test"},
        created_at_ms=1,
    ))
    assert repository.get_session_activity_version(session_id="session-activity") == 1


def test_versioned_api_root_lists_modules() -> None:
    response = client.get("/api/v1")
    assert response.status_code == 200
    payload = unwrap(response)
    assert payload["apiPrefix"] == "/api/v1"
    assert any(item["feature"] == "authentication" for item in payload["modules"])
    assert any(item["feature"] == "resume" for item in payload["modules"])
    assert any(item["feature"] == "live-answer" for item in payload["modules"])
    assert any(item["feature"] == "realtime-speech" for item in payload["modules"])
    assert any(item["feature"] == "knowledge-retrieval" for item in payload["modules"])
    assert any(item["feature"] == "session" for item in payload["modules"])


def test_foundation_index_and_ownership_are_available() -> None:
    foundation = client.get("/api/v1/system/foundation")
    ownership = client.get("/api/v1/system/ownership")
    assert foundation.status_code == 200
    assert ownership.status_code == 200
    assert any(module["feature"] == "knowledge" for module in unwrap(foundation)["modules"])
    assert any(item["app"] == "apps/backend" for item in unwrap(ownership))


def test_placeholder_endpoints_return_uniform_shape() -> None:
    screenshot = client.get("/api/v1/screenshot-answer/status")
    assert screenshot.status_code == 200
    assert unwrap(screenshot)["feature"] == "screenshot-answer"


def test_authentication_register_login_refresh_logout_and_multi_device_sessions() -> None:
    registered = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": "alice@example.com",
        "password": "Password123!",
        "displayName": "Alice",
        "clientLabel": "web-chrome",
    }))
    assert registered["user"]["loginId"] == "alice@example.com"
    assert registered["user"]["displayName"] == "Alice"
    assert registered["tokens"]["accessToken"]
    assert registered["tokens"]["refreshToken"]

    duplicate = client.post("/api/v1/auth/register", json={
        "loginId": "alice@example.com",
        "password": "Password123!",
    })
    assert duplicate.status_code == 409

    invalid_login = client.post("/api/v1/auth/login", json={
        "loginId": "alice@example.com",
        "password": "wrong-password",
    })
    assert invalid_login.status_code == 401

    web_login = unwrap(client.post("/api/v1/auth/login", json={
        "loginId": "alice@example.com",
        "password": "Password123!",
        "clientLabel": "web-safari",
    }))
    mobile_login = unwrap(client.post("/api/v1/auth/login", json={
        "loginId": "alice@example.com",
        "password": "Password123!",
        "clientLabel": "mobile-app",
    }))
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {web_login['tokens']['accessToken']}"})
    assert me.status_code == 200
    assert unwrap(me)["loginId"] == "alice@example.com"

    sessions = unwrap(client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {web_login['tokens']['accessToken']}"}))
    assert len(sessions["sessions"]) >= 3
    assert any(item["clientLabel"] == "mobile-app" and item["status"] == "active" for item in sessions["sessions"])

    refreshed = unwrap(client.post("/api/v1/auth/refresh", json={"refreshToken": web_login["tokens"]["refreshToken"]}))
    assert refreshed["user"]["userId"] == web_login["user"]["userId"]
    assert refreshed["authSessionId"] == web_login["authSessionId"]
    revoked_refresh = client.post("/api/v1/auth/refresh", json={"refreshToken": web_login["tokens"]["refreshToken"]})
    assert revoked_refresh.status_code == 401

    logout = unwrap(client.post(
        "/api/v1/auth/logout",
        json={"logoutAllDevices": False},
        headers={"Authorization": f"Bearer {mobile_login['tokens']['accessToken']}"},
    ))
    assert mobile_login["authSessionId"] in logout["revokedSessionIds"]
    sessions_after = unwrap(client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {refreshed['tokens']['accessToken']}"}))
    mobile_session = next(item for item in sessions_after["sessions"] if item["authSessionId"] == mobile_login["authSessionId"])
    assert mobile_session["status"] == "revoked"

    me_missing = client.get("/api/v1/auth/me")
    assert me_missing.status_code == 401


def test_expired_auth_sessions_are_persisted_as_expired() -> None:
    from dataclasses import replace
    from app.deps import authentication_repository

    primary = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": "expired-sessions@example.com",
        "password": "Password123!",
        "clientLabel": "primary-browser",
    }))
    secondary = unwrap(client.post("/api/v1/auth/login", json={
        "loginId": "expired-sessions@example.com",
        "password": "Password123!",
        "clientLabel": "old-browser",
    }))
    repository = authentication_repository()
    stale = repository.get_auth_session(secondary["authSessionId"])
    assert stale is not None
    repository.save_auth_session(replace(stale, expires_at_ms=1))

    listing = unwrap(client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {primary['tokens']['accessToken']}"},
    ))
    expired = next(item for item in listing["sessions"] if item["authSessionId"] == secondary["authSessionId"])
    assert expired["status"] == "expired"
    assert repository.get_auth_session(secondary["authSessionId"]).status == "expired"


def test_wechat_authorization_session_supports_scan_authorize_and_replay_protection() -> None:
    created = unwrap(client.post("/api/v1/auth/wechat/authorization-sessions", json={"clientLabel": "web-wechat"}))
    assert created["status"] == "waiting"
    assert created["authRequestId"]
    assert created["qrCodeText"]

    scanned = unwrap(client.post(f"/api/v1/auth/wechat/authorization-sessions/{created['authRequestId']}/scan"))
    assert scanned["status"] == "scanned"

    authorized = unwrap(client.post(f"/api/v1/auth/wechat/authorization-sessions/{created['authRequestId']}/authorize"))
    assert authorized["status"] == "authorized"
    assert authorized["result"]["tokens"]["accessToken"]
    assert authorized["result"]["user"]["loginProvider"] == "wechat"
    assert authorized["result"]["user"]["lastLoginAtMs"] >= authorized["result"]["user"]["createdAtMs"]

    me = unwrap(client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {authorized['result']['tokens']['accessToken']}"}))
    assert me["userId"] == authorized["result"]["user"]["userId"]
    assert me["bindings"][0]["provider"] == "wechat"

    replay = client.post("/api/v1/auth/wechat/callback", json={"state": "invalid-state", "code": "code-replay"})
    assert replay.status_code == 401


def test_sms_authentication_sends_code_registers_and_reuses_phone_identity() -> None:
    phone = "13900001234"
    sent = unwrap(client.post("/api/v1/auth/sms/send-code", json={"phoneNumber": phone, "clientLabel": "web-sms"}))
    assert sent["challengeId"].startswith("sms-challenge-")
    assert sent["status"] == "sent"
    assert sent["maskedPhone"] == "139****1234"

    invalid = client.post("/api/v1/auth/sms/verify-login", json={"phoneNumber": phone, "challengeId": sent["challengeId"], "code": "000000"})
    assert invalid.status_code == 401
    assert invalid.json()["error"]["message"] == "验证码不正确或已过期，请检查后重新输入。"

    verified = unwrap(client.post("/api/v1/auth/sms/verify-login", json={"phoneNumber": phone, "challengeId": sent["challengeId"], "code": "123456", "clientLabel": "web-sms"}))
    assert verified["user"]["loginProvider"] == "sms"
    assert verified["user"]["bindings"][0]["provider"] == "sms"
    assert verified["tokens"]["accessToken"]

    me = unwrap(client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {verified['tokens']['accessToken']}"}))
    assert me["userId"] == verified["user"]["userId"]

    from app.deps import authentication_repository

    repository = authentication_repository()
    latest = repository.list_sms_challenges_for_phone(phone_hash=repository.get_sms_challenge(sent["challengeId"]).phone_hash)[0]
    repository.save_sms_challenge(latest.__class__(**{**latest.__dict__, "created_at_ms": 1, "updated_at_ms": 1}))

    sent_again = unwrap(client.post("/api/v1/auth/sms/send-code", json={"phoneNumber": phone, "clientLabel": "web-sms-2"}))
    logged_in_again = unwrap(client.post("/api/v1/auth/sms/verify-login", json={"phoneNumber": phone, "challengeId": sent_again["challengeId"], "code": "123456", "clientLabel": "web-sms-2"}))
    assert logged_in_again["user"]["userId"] == verified["user"]["userId"]


def test_aliyun_personal_developer_sms_provider_uses_model_verify_result() -> None:
    settings = Settings(
        auth_sms_aliyun_access_key_id="test-key",
        auth_sms_aliyun_access_key_secret="test-secret",
        auth_sms_aliyun_sign_name="系统赠送签名",
        auth_sms_aliyun_template_code="SMS_000000",
    )
    provider = AliyunDypnsSmsVerificationProvider(settings)
    calls: list[dict[str, str]] = []

    def fake_request(payload: dict[str, str]) -> dict:
        calls.append(payload)
        if payload["Action"] == "SendSmsVerifyCode":
            return {"Code": "OK", "RequestId": "send-request", "Model": {"BizId": "biz-from-model"}}
        if payload["VerifyCode"] == "000000":
            return {"Code": "OK", "RequestId": "invalid-request", "Model": {"VerifyResult": "UNKNOWN"}}
        return {"Code": "OK", "RequestId": "verify-request", "Model": {"VerifyResult": "PASS"}}

    provider._request = fake_request  # type: ignore[method-assign]
    sent = provider.send_code(phone_e164="+8613900001234", challenge_id="sms-challenge-test")
    assert sent.outcome == "sent"
    assert sent.provider_biz_id == "biz-from-model"
    assert calls[0]["CountryCode"] == "86"
    assert calls[0]["PhoneNumber"] == "13900001234"
    assert calls[0]["SignName"] == "系统赠送签名"
    assert calls[0]["TemplateCode"] == "SMS_000000"
    assert calls[0]["OutId"] == "sms-challenge-test"

    challenge = SmsChallengeRecord(
        challenge_id="sms-challenge-test",
        phone_e164="+8613900001234",
        phone_hash="phone-hash",
        provider="aliyun-dypnsapi",
        status="sent",
        provider_biz_id=sent.provider_biz_id,
        provider_request_id=sent.provider_request_id,
        attempt_count=0,
        max_attempts=5,
        expires_at_ms=9999999999999,
        created_at_ms=1,
        updated_at_ms=1,
    )
    verified = provider.verify_code(phone_e164="+8613900001234", code="123456", challenge=challenge)
    assert verified.outcome == "verified"
    assert calls[1]["CountryCode"] == "86"
    assert calls[1]["PhoneNumber"] == "13900001234"
    assert calls[1]["VerifyCode"] == "123456"
    assert calls[1]["OutId"] == "sms-challenge-test"

    invalid = provider.verify_code(phone_e164="+8613900001234", code="000000", challenge=challenge)
    assert invalid.outcome == "invalid"
    assert invalid.provider_request_id == "invalid-request"


def test_aliyun_dysmsapi_provider_sends_code_and_verifies_digest_only(monkeypatch) -> None:
    settings = Settings(
        auth_sms_provider_mode="aliyun-dysmsapi",
        auth_sms_aliyun_endpoint="https://dysmsapi.aliyuncs.com",
        auth_sms_aliyun_region_id="cn-qingdao",
        auth_sms_aliyun_access_key_id="test-key",
        auth_sms_aliyun_access_key_secret="test-secret",
        auth_sms_aliyun_sign_name="杭州临平知界智能技术",
        auth_sms_aliyun_template_code="SMS_336645096",
        auth_sms_code_pepper="test-only-code-pepper-at-least-32-bytes",
    )
    provider = AliyunDysmsSmsVerificationProvider(settings)
    calls: list[dict[str, str]] = []
    monkeypatch.setattr("app.services.sms_verification_provider.secrets.randbelow", lambda _limit: 123456)

    def fake_request(payload: dict[str, str]) -> dict:
        calls.append(payload)
        return {"Code": "OK", "RequestId": "send-request", "BizId": "send-biz"}

    provider._request = fake_request  # type: ignore[method-assign]
    sent = provider.send_code(phone_e164="+8613900001234", challenge_id="sms-challenge-dysms")
    assert sent.outcome == "sent"
    assert sent.verification_code_digest
    assert "123456" not in sent.verification_code_digest
    assert calls == [{
        "Action": "SendSms",
        "PhoneNumbers": "13900001234",
        "SignName": "杭州临平知界智能技术",
        "TemplateCode": "SMS_336645096",
        "TemplateParam": '{"code":"123456"}',
        "OutId": "sms-challenge-dysms",
    }]
    challenge = SmsChallengeRecord(
        challenge_id="sms-challenge-dysms",
        phone_e164="+8613900001234",
        phone_hash="phone-hash",
        provider="aliyun-dysmsapi",
        status="sent",
        provider_biz_id=sent.provider_biz_id,
        provider_request_id=sent.provider_request_id,
        attempt_count=0,
        max_attempts=5,
        expires_at_ms=9999999999999,
        created_at_ms=1,
        updated_at_ms=1,
        code_digest=sent.verification_code_digest,
    )
    assert provider.verify_code(phone_e164="+8613900001234", code="123456", challenge=challenge).outcome == "verified"
    assert provider.verify_code(phone_e164="+8613900001234", code="654321", challenge=challenge).outcome == "invalid"


def test_wechat_authorization_session_expires_and_requires_refresh() -> None:
    created = unwrap(client.post("/api/v1/auth/wechat/authorization-sessions", json={"clientLabel": "web-wechat-expired"}))
    assert created["status"] == "waiting"

    from app.deps import authentication_repository

    repository = authentication_repository()
    record = repository.get_wechat_authorization_session(created["authRequestId"])
    assert record is not None
    repository.save_wechat_authorization_session(record.__class__(
        **{**record.__dict__, "expires_at_ms": 1}
    ))

    expired = unwrap(client.get(f"/api/v1/auth/wechat/authorization-sessions/{created['authRequestId']}"))
    assert expired["status"] == "expired"
    assert expired["errorCode"] == "expired"

    authorize = client.post(f"/api/v1/auth/wechat/authorization-sessions/{created['authRequestId']}/authorize")
    assert authorize.status_code == 401


def test_resume_upload_intent_and_completion_flow() -> None:
    intent = client.post("/api/v1/resume/upload-intents", json={
        "userId": "prototype-user",
        "filename": "resume.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 1024,
    })
    assert intent.status_code == 200
    payload = unwrap(intent)
    assert payload["materialKind"] == "resume"
    assert payload["fileKind"] == "pdf"
    complete = client.post("/api/v1/resume/uploads/complete", json={
        "userId": "prototype-user",
        "intentId": payload["intentId"],
        "objectKey": payload["objectKey"],
        "contentType": "application/pdf",
        "sizeBytes": 1024,
        "etag": "demo-etag",
    })
    assert complete.status_code == 200
    completed_payload = unwrap(complete)
    assert completed_payload["source"]["processingState"] == "processing"
    documents = client.get("/api/v1/documents", params={"userId": "prototype-user"})
    listed = unwrap(documents)
    matched = next(item for item in listed if item["documentKind"] == "resume")
    assert matched["status"] in {"processing_requested", "processing", "ready"}
    processing = wait_for_task_stage(completed_payload["source"]["sourceId"], "prototype-user", "COMPLETED")
    assert processing["readyForAi"] is True
    assert processing["latestTask"]["chunkCount"] == 0


def test_upload_validation_rejects_unsupported_formats() -> None:
    response = client.post("/api/v1/resume/upload-intents", json={
        "userId": "prototype-user",
        "filename": "resume.png",
        "contentType": "image/png",
        "sizeBytes": 1024,
    })
    assert response.status_code == 400
    assert "PDF" in response.json()["error"]["message"]


def test_upload_validation_rejects_oversized_files() -> None:
    response = client.post("/api/v1/resume/upload-intents", json={
        "userId": "prototype-user",
        "filename": "resume.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 25 * 1024 * 1024,
    })
    assert response.status_code == 400
    assert "20 MB" in response.json()["error"]["message"]


def test_expired_upload_intent_is_rejected() -> None:
    intent = client.post("/api/v1/resume/upload-intents", json={
        "userId": "prototype-user",
        "filename": "resume.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 1024,
    })
    intent = unwrap(intent)
    from app.deps import storage_port

    storage = storage_port()
    storage.issued_intents[intent["intentId"]] = storage.issued_intents[intent["intentId"]].__class__(
        **{**storage.issued_intents[intent["intentId"]].__dict__, "expires_at_ms": 1}
    )
    response = client.post("/api/v1/resume/uploads/complete", json={
        "userId": "prototype-user",
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "application/pdf",
        "sizeBytes": 1024,
    })
    assert response.status_code == 410


def test_knowledge_completion_checks_collection_ownership() -> None:
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": "owner-a",
        "name": "算法题",
    }))
    intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents", json={
        "userId": "owner-b",
        "filename": "notes.md",
        "contentType": "text/markdown",
        "sizeBytes": 2048,
    }))
    response = client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": "owner-b",
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 2048,
        "confirmIndexCharge": True,
    })
    assert response.status_code == 403


def test_knowledge_completion_requires_explicit_index_charge_confirmation() -> None:
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": "knowledge-charge-confirmation",
        "name": "计费确认资料库",
    }))
    intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents", json={
        "userId": "knowledge-charge-confirmation",
        "filename": "notes.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    response = client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": "knowledge-charge-confirmation",
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    })
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "请先确认知识资料索引报价。"


def test_document_object_keys_are_unique_for_same_filename() -> None:
    first = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "prototype-user",
        "filename": "resume.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 1024,
    }))
    second = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "prototype-user",
        "filename": "resume.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 1024,
    }))
    assert first["objectKey"] != second["objectKey"]


def test_document_detail_and_delete_are_permission_controlled() -> None:
    intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "owner-a",
        "filename": "resume.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 1024,
    }))
    complete = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": "owner-a",
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "application/pdf",
        "sizeBytes": 1024,
    }))
    document_id = complete["source"]["sourceId"]
    detail = client.get(f"/api/v1/documents/{document_id}", params={"userId": "owner-a"})
    assert detail.status_code == 200
    assert unwrap(detail)["documentId"] == document_id
    forbidden = client.delete(f"/api/v1/documents/{document_id}", params={"userId": "owner-b"})
    assert forbidden.status_code == 403
    deleted = client.delete(f"/api/v1/documents/{document_id}", params={"userId": "owner-a"})
    assert deleted.status_code == 200
    assert unwrap(deleted)["status"] == "deleted"
    listing = unwrap(client.get("/api/v1/documents", params={"userId": "owner-a"}))
    assert all(item["documentId"] != document_id for item in listing)


def test_ready_document_can_be_disabled_and_reenabled_without_reprocessing() -> None:
    intent = unwrap(client.post("/api/v1/job-descriptions/upload-intents", json={
        "userId": "availability-owner",
        "filename": "availability.md",
        "contentType": "text/markdown",
        "sizeBytes": 256,
    }))
    complete = unwrap(client.post("/api/v1/job-descriptions/uploads/complete", json={
        "userId": "availability-owner",
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 256,
    }))
    document_id = complete["source"]["sourceId"]
    wait_for_task_stage(document_id, "availability-owner", "COMPLETED")

    disabled = client.patch(f"/api/v1/documents/{document_id}/availability", json={
        "userId": "availability-owner",
        "enabled": False,
    })
    assert disabled.status_code == 200
    assert unwrap(disabled)["indexState"] == "disabled"

    forbidden = client.patch(f"/api/v1/documents/{document_id}/availability", json={
        "userId": "another-owner",
        "enabled": True,
    })
    assert forbidden.status_code == 403

    enabled = client.patch(f"/api/v1/documents/{document_id}/availability", json={
        "userId": "availability-owner",
        "enabled": True,
    })
    assert enabled.status_code == 200
    enabled_payload = unwrap(enabled)
    assert enabled_payload["status"] == "ready"
    assert enabled_payload["indexState"] == "indexed"
    assert enabled_payload["summary"] == "已恢复使用，可在面试准备中选择。"
    status = unwrap(client.get(f"/api/v1/document-processing/documents/{document_id}", params={"userId": "availability-owner"}))
    assert status["latestTask"]["currentStage"] == "COMPLETED"


def test_deleting_one_knowledge_document_preserves_disabled_sibling_state() -> None:
    stamp = int(time() * 1_000_000)
    authentication = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": f"material-state-{stamp}@example.com",
        "password": "SyntheticMaterialState123@",
        "displayName": "Material state regression",
        "clientLabel": "material-state-test",
    }))
    owner = authentication["user"]["userId"]
    headers = {"Authorization": f"Bearer {authentication['tokens']['accessToken']}"}
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": owner,
        "name": "状态保持回归资料库",
    }, headers=headers))

    document_ids: list[str] = []
    for index in range(2):
        intent = unwrap(client.post(
            f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents",
            json={
                "userId": owner,
                "filename": f"state-{index}.md",
                "contentType": "text/markdown",
                "sizeBytes": 128,
            },
            headers=headers,
        ))
        completed = unwrap(client.post(
            f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete",
            json={
                "userId": owner,
                "intentId": intent["intentId"],
                "objectKey": intent["objectKey"],
                "contentType": "text/markdown",
                "sizeBytes": 128,
                "etag": f"synthetic-material-state-{index}",
                "contentSha256": f"{index + 1}" * 64,
                "confirmIndexCharge": True,
            },
            headers=headers,
        ))
        document_id = completed["source"]["sourceId"]
        wait_for_task_stage(document_id, owner, "COMPLETED")
        document_ids.append(document_id)

    disabled_id, deleted_id = document_ids
    disabled = client.patch(
        f"/api/v1/documents/{disabled_id}/availability",
        json={"userId": owner, "enabled": False},
        headers=headers,
    )
    assert disabled.status_code == 200
    deleted = client.delete(
        f"/api/v1/documents/{deleted_id}",
        params={"userId": owner},
        headers=headers,
    )
    assert deleted.status_code == 200

    refreshed = unwrap(client.get("/api/v1/web/state", headers=headers))
    sibling_document = next(item for item in refreshed["knowledgeDocuments"] if item["id"] == disabled_id)
    sibling_source = next(item for item in refreshed["librarySources"] if item["id"] == disabled_id)
    assert sibling_document["status"] == "disabled"
    assert sibling_document["indexState"] == "disabled"
    assert sibling_document["syncStatus"] == "synced"
    assert sibling_source["status"] == "disabled"
    assert sibling_source["indexState"] == "disabled"
    assert sibling_source["syncStatus"] == "synced"
    assert all(item["id"] != deleted_id for item in refreshed["knowledgeDocuments"])


def test_processing_handoff_boundary_exposes_uploaded_knowledge_documents() -> None:
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": "owner-handoff",
        "name": "系统设计",
    }))
    intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents", json={
        "userId": "owner-handoff",
        "filename": "notes.md",
        "contentType": "text/markdown",
        "sizeBytes": 2048,
    }))
    client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": "owner-handoff",
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 2048,
        "confirmIndexCharge": True,
    })
    response = client.get("/api/v1/documents/processing/handoffs", params={"userId": "owner-handoff"})
    assert response.status_code == 200
    payload = unwrap(response)
    assert any(item["documentKind"] == "knowledge" and item["status"] in {"processing_requested", "processing", "ready"} for item in payload)


def test_document_processing_status_and_retry_api() -> None:
    intent = unwrap(client.post("/api/v1/job-descriptions/upload-intents", json={
        "userId": "processing-user",
        "filename": "jd.md",
        "contentType": "text/markdown",
        "sizeBytes": 512,
    }))
    complete = unwrap(client.post("/api/v1/job-descriptions/uploads/complete", json={
        "userId": "processing-user",
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 512,
    }))
    document_id = complete["source"]["sourceId"]
    status = wait_for_task_stage(document_id, "processing-user", "COMPLETED")
    task_id = status["latestTask"]["taskId"]

    task_response = client.get(f"/api/v1/document-processing/tasks/{task_id}", params={"userId": "processing-user"})
    assert task_response.status_code == 200
    assert unwrap(task_response)["taskId"] == task_id

    retry_response = client.post(f"/api/v1/document-processing/tasks/{task_id}/retry", json={"userId": "processing-user"})
    assert retry_response.status_code == 200
    retry_payload = unwrap(retry_response)
    assert retry_payload["currentStage"] == "QUEUED"

    retried_status = wait_for_task_stage(document_id, "processing-user", "COMPLETED")
    assert retried_status["latestTask"]["retryCount"] >= 0
    assert any(event["eventName"] == "task_requeued_manual" for event in retried_status["events"])
    assert any(event["eventName"] == "parser_started" for event in retried_status["events"])
    assert any(event["eventName"] == "parser_succeeded" for event in retried_status["events"])
    assert not any(event["eventName"] == "embedding_chunking_started" for event in retried_status["events"])
    assert not any(event["eventName"] == "embedding_started" for event in retried_status["events"])
    assert not any(event["eventName"] == "vector_writing_started" for event in retried_status["events"])
    assert retried_status["latestTask"]["parserProvider"] in {"text-parser", "inline-text", "mineru", "normalized-artifact-cache"}


def test_runtime_overview_exposes_infrastructure_boundaries() -> None:
    response = client.get("/api/v1/system/runtime")
    assert response.status_code == 200
    payload = unwrap(response)
    settings = get_settings()
    assert payload["database"]["configured"] is bool(settings.database_url)
    assert payload["pgvector"]["extensionAvailable"] in {True, False}
    assert payload["retrieval"]["retrievalPort"] == "knowledge-retrieval-service"


def test_knowledge_retrieval_returns_structured_multi_source_context() -> None:
    resume_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "retrieval-user",
        "filename": "resume.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    resume_complete = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": "retrieval-user",
        "intentId": resume_intent["intentId"],
        "objectKey": resume_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": "retrieval-user",
        "name": "项目经历",
    }))
    knowledge_intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents", json={
        "userId": "retrieval-user",
        "filename": "knowledge.md",
        "contentType": "text/markdown",
        "sizeBytes": 256,
    }))
    knowledge_complete = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": "retrieval-user",
        "intentId": knowledge_intent["intentId"],
        "objectKey": knowledge_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 256,
        "confirmIndexCharge": True,
    }))
    wait_for_task_stage(resume_complete["source"]["sourceId"], "retrieval-user", "COMPLETED")
    wait_for_task_stage(knowledge_complete["source"]["sourceId"], "retrieval-user", "COMPLETED")

    response = client.post("/api/v1/knowledge-retrieval/context", json={
        "question": "请帮我提取和项目经历相关的内容",
        "filter": {
            "ownerUserId": "retrieval-user",
            "documentKinds": ["resume", "knowledge"],
            "knowledgeCollectionIds": [collection["collectionId"]],
        },
        "candidateTopK": 4,
        "finalTopK": 4,
    })
    assert response.status_code == 200
    payload = unwrap(response)
    assert payload["normalizedQuestion"] == "请帮我提取和项目经历相关的内容"
    assert payload["candidateCount"] >= payload["finalCount"] >= 1
    assert payload["contextText"] != ""
    assert all(chunk["documentKind"] in {"resume", "knowledge"} for chunk in payload["chunks"])
    assert all(chunk["metadata"]["ownerUserId"] == "retrieval-user" for chunk in payload["chunks"])
    assert any(chunk["documentId"] == knowledge_complete["source"]["sourceId"] for chunk in payload["chunks"])


def test_resume_documents_are_excluded_from_knowledge_retrieval() -> None:
    owner_a_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "owner-a-retrieval",
        "filename": "resume-a.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    owner_a_complete = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": "owner-a-retrieval",
        "intentId": owner_a_intent["intentId"],
        "objectKey": owner_a_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    owner_b_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "owner-b-retrieval",
        "filename": "resume-b.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": "owner-b-retrieval",
        "intentId": owner_b_intent["intentId"],
        "objectKey": owner_b_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    wait_for_task_stage(owner_a_complete["source"]["sourceId"], "owner-a-retrieval", "COMPLETED")

    response = client.post("/api/v1/knowledge-retrieval/context", json={
        "question": "帮我找出候选人的经历",
        "filter": {
            "ownerUserId": "owner-a-retrieval",
            "documentKinds": ["resume"],
        },
    })
    assert response.status_code == 200
    payload = unwrap(response)
    assert payload["finalCount"] == 0
    assert all(chunk["metadata"]["ownerUserId"] == "owner-a-retrieval" for chunk in payload["chunks"])


def test_interview_session_lifecycle_materials_context_and_usage() -> None:
    resume_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "session-user",
        "filename": "resume.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    resume_complete = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": "session-user",
        "intentId": resume_intent["intentId"],
        "objectKey": resume_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    jd_intent = unwrap(client.post("/api/v1/job-descriptions/upload-intents", json={
        "userId": "session-user",
        "filename": "jd.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    jd_complete = unwrap(client.post("/api/v1/job-descriptions/uploads/complete", json={
        "userId": "session-user",
        "intentId": jd_intent["intentId"],
        "objectKey": jd_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": "session-user",
        "name": "面经资料",
    }))
    knowledge_intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents", json={
        "userId": "session-user",
        "filename": "knowledge.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    knowledge_complete = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": "session-user",
        "intentId": knowledge_intent["intentId"],
        "objectKey": knowledge_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
        "confirmIndexCharge": True,
    }))
    wait_for_task_stage(resume_complete["source"]["sourceId"], "session-user", "COMPLETED")
    wait_for_task_stage(jd_complete["source"]["sourceId"], "session-user", "COMPLETED")
    wait_for_task_stage(knowledge_complete["source"]["sourceId"], "session-user", "COMPLETED")

    created = unwrap(client.post("/api/v1/sessions", json={
        "userId": "session-user",
        "title": "后端开发面试",
    }))
    session_id = created["sessionId"]
    assert created["status"] == "preparing"
    assert created["continueTarget"] == "preparing"

    confirmed = unwrap(client.post(f"/api/v1/sessions/{session_id}/materials/confirm", json={
        "userId": "session-user",
        "resumeDocumentId": resume_complete["source"]["sourceId"],
        "jobDescriptionDocumentId": jd_complete["source"]["sourceId"],
        "knowledgeDocumentIds": [knowledge_complete["source"]["sourceId"]],
    }))
    assert confirmed["materialBinding"]["revision"] == 1
    assert confirmed["materialBinding"]["resumeDocumentId"] == resume_complete["source"]["sourceId"]
    assert confirmed["integrationReferences"][0]["name"] == "knowledge-retrieval"

    started = unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "session-user"}))
    assert started["status"] == "live"
    assert started["continueTarget"] == "live"

    unwrap(client.post(f"/api/v1/sessions/{session_id}/context", json={
        "userId": "session-user",
        "role": "interviewer",
        "sourceKind": "system-audio",
        "content": "请介绍一下你最近的项目。",
        "visibility": "session",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/context", json={
        "userId": "session-user",
        "role": "candidate",
        "sourceKind": "microphone",
        "content": "我最近做了一个检索增强问答项目。",
        "visibility": "ai",
    }))
    context_window = unwrap(client.get(f"/api/v1/sessions/{session_id}/context", params={"userId": "session-user"}))
    assert context_window["totalCount"] == 2
    assert context_window["entries"][0]["role"] == "interviewer"
    assert context_window["entries"][1]["role"] == "candidate"

    usage_updated = unwrap(client.post(f"/api/v1/sessions/{session_id}/usage", json={
        "userId": "session-user",
        "usageKind": "prompt",
        "promptTokens": 120,
        "completionTokens": 80,
        "totalTokens": 200,
        "providerName": "mock-llm",
        "modelName": "mock-model",
    }))
    assert usage_updated["usageTotals"]["totalTokens"] == 200
    usage = unwrap(client.get(f"/api/v1/sessions/{session_id}/usage", params={"userId": "session-user"}))
    assert usage["totals"]["recordCount"] == 1
    assert usage["records"][0]["providerName"] == "mock-llm"

    continued = unwrap(client.post(f"/api/v1/sessions/{session_id}/continue", json={"userId": "session-user"}))
    assert continued["target"] == "live"
    assert continued["session"]["sessionId"] == session_id

    ended = unwrap(client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": "session-user"}))
    assert ended["status"] == "ended"
    assert ended["continueTarget"] == "history"

    restarted = unwrap(client.post(f"/api/v1/sessions/{session_id}/restart", json={"userId": "session-user"}))
    assert restarted["restartOfSessionId"] == session_id
    assert restarted["status"] == "preparing"
    assert restarted["materialBinding"]["resumeDocumentId"] == resume_complete["source"]["sourceId"]
    assert restarted["materialBinding"]["knowledgeDocumentIds"] == [knowledge_complete["source"]["sourceId"]]


def test_session_detail_preserves_bound_document_history_after_delete() -> None:
    resume_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "session-history-user",
        "filename": "resume.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    resume_complete = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": "session-history-user",
        "intentId": resume_intent["intentId"],
        "objectKey": resume_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    wait_for_task_stage(resume_complete["source"]["sourceId"], "session-history-user", "COMPLETED")
    created = unwrap(client.post("/api/v1/sessions", json={
        "userId": "session-history-user",
        "title": "删除资料后的历史保持",
    }))
    session_id = created["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/materials/confirm", json={
        "userId": "session-history-user",
        "resumeDocumentId": resume_complete["source"]["sourceId"],
        "knowledgeDocumentIds": [],
    }))
    deleted = client.delete(f"/api/v1/documents/{resume_complete['source']['sourceId']}", params={"userId": "session-history-user"})
    assert deleted.status_code == 200
    detail = unwrap(client.get(f"/api/v1/sessions/{session_id}", params={"userId": "session-history-user"}))
    assert detail["materialBinding"]["boundDocuments"][0]["documentId"] == resume_complete["source"]["sourceId"]
    assert detail["materialBinding"]["boundDocuments"][0]["active"] is False
    assert detail["materialBinding"]["boundDocuments"][0]["status"] == "deleted"


def test_web_state_is_scoped_to_authenticated_user() -> None:
    user_a = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": "web-state-a@example.com",
        "password": "Password123!",
        "displayName": "Web State A",
    }))
    user_b = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": "web-state-b@example.com",
        "password": "Password123!",
        "displayName": "Web State B",
    }))
    user_a_id = user_a["user"]["userId"]
    user_b_id = user_b["user"]["userId"]

    a_resume_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": user_a_id,
        "filename": "resume-a.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    a_payload = b"# A resume\n" + b"a" * 117
    unwrap(client.post("/api/v1/resume/uploads/proxy", data={
        "userId": user_a_id,
        "intentId": a_resume_intent["intentId"],
        "objectKey": a_resume_intent["objectKey"],
        "contentType": "text/markdown",
    }, files={"file": ("resume-a.md", a_payload, "text/markdown")}))
    a_resume = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": user_a_id,
        "intentId": a_resume_intent["intentId"],
        "objectKey": a_resume_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    b_resume_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": user_b_id,
        "filename": "resume-b.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    b_payload = b"# B resume\n" + b"b" * 117
    unwrap(client.post("/api/v1/resume/uploads/proxy", data={
        "userId": user_b_id,
        "intentId": b_resume_intent["intentId"],
        "objectKey": b_resume_intent["objectKey"],
        "contentType": "text/markdown",
    }, files={"file": ("resume-b.md", b_payload, "text/markdown")}))
    b_resume = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": user_b_id,
        "intentId": b_resume_intent["intentId"],
        "objectKey": b_resume_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    a_session = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_a_id,
        "title": "A 的面试",
    }))
    b_session = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_b_id,
        "title": "B 的面试",
    }))

    anonymous = unwrap(client.get("/api/v1/web/state"))
    assert anonymous["account"]["id"] == "anonymous"
    assert anonymous["interviews"] == []
    assert anonymous["librarySources"] == []

    state_a = unwrap(client.get("/api/v1/web/state", headers={
        "Authorization": f"Bearer {user_a['tokens']['accessToken']}",
    }))
    assert state_a["account"]["id"] == user_a_id
    assert state_a["billing"]["balance"] == 200
    assert any(item["id"] == a_session["sessionId"] for item in state_a["interviews"])
    assert all(item["id"] != b_session["sessionId"] for item in state_a["interviews"])
    assert any(item["id"] == a_resume["source"]["sourceId"] for item in state_a["librarySources"])
    assert all(item["id"] != b_resume["source"]["sourceId"] for item in state_a["librarySources"])
    assert all(item["ownerUserId"] == user_a_id for item in state_a["librarySources"])

    state_b = unwrap(client.get("/api/v1/web/state", headers={
        "Authorization": f"Bearer {user_b['tokens']['accessToken']}",
    }))
    assert state_b["account"]["id"] == user_b_id
    assert any(item["id"] == b_session["sessionId"] for item in state_b["interviews"])
    assert all(item["id"] != a_session["sessionId"] for item in state_b["interviews"])
    assert any(item["id"] == b_resume["source"]["sourceId"] for item in state_b["librarySources"])
    assert all(item["id"] != a_resume["source"]["sourceId"] for item in state_b["librarySources"])


def test_live_answer_chat_service_generates_history_and_usage() -> None:
    resume_intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": "chat-user",
        "filename": "resume.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    resume_complete = unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": "chat-user",
        "intentId": resume_intent["intentId"],
        "objectKey": resume_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": "chat-user",
        "name": "项目资料",
    }))
    knowledge_intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents", json={
        "userId": "chat-user",
        "filename": "knowledge.md",
        "contentType": "text/markdown",
        "sizeBytes": 128,
    }))
    knowledge_complete = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": "chat-user",
        "intentId": knowledge_intent["intentId"],
        "objectKey": knowledge_intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": 128,
        "confirmIndexCharge": True,
    }))
    wait_for_task_stage(resume_complete["source"]["sourceId"], "chat-user", "COMPLETED")
    wait_for_task_stage(knowledge_complete["source"]["sourceId"], "chat-user", "COMPLETED")
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-user",
        "title": "实时问答测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/materials/confirm", json={
        "userId": "chat-user",
        "resumeDocumentId": resume_complete["source"]["sourceId"],
        "knowledgeDocumentIds": [knowledge_complete["source"]["sourceId"]],
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-user"}))

    answer = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": "chat-user",
        "sessionId": session_id,
        "question": "请介绍一个与你最近项目最相关的亮点",
        "stream": True,
    }))
    assert answer["task"]["status"] == "completed"
    assert answer["task"]["providerName"] == "qwen-compatible"
    assert answer["task"]["promptTemplateId"] == "interview-chat-system"
    assert answer["task"]["promptVersion"] == "v4"
    assert answer["task"]["retrievalExcerptCount"] >= 0
    assert len(answer["task"]["chunks"]) >= 2
    assert answer["task"]["chunks"][-1]["isFinal"] is True

    task = unwrap(client.get(f"/api/v1/live-answer/tasks/{answer['task']['taskId']}", params={"userId": "chat-user"}))
    assert task["taskId"] == answer["task"]["taskId"]
    history = unwrap(client.get(f"/api/v1/live-answer/sessions/{session_id}/history", params={"userId": "chat-user"}))
    assert len(history) >= 1
    assert history[0]["question"] == "请介绍一个与你最近项目最相关的亮点"
    context = unwrap(client.get(f"/api/v1/sessions/{session_id}/context", params={"userId": "chat-user"}))
    assert any(item["role"] == "manual-question" for item in context["entries"])
    assert any(item["role"] == "assistant" for item in context["entries"])
    usage = unwrap(client.get(f"/api/v1/sessions/{session_id}/usage", params={"userId": "chat-user"}))
    assert usage["totals"]["totalTokens"] > 0
    assert usage["records"][-1]["providerName"] == "qwen-compatible"


def test_live_answer_retries_once_then_completes() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-retry-user",
        "title": "重试测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-retry-user"}))
    answer = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": "chat-retry-user",
        "sessionId": session_id,
        "question": "__retry_once__ 请总结一个项目亮点",
        "stream": True,
    }))
    assert answer["task"]["status"] == "completed"
    assert answer["task"]["retryCount"] == 1


def test_live_answer_can_use_remote_gateway_contract_without_synthetic_copy(monkeypatch) -> None:
    monkeypatch.setattr(QwenCompatibleGateway, "_should_use_remote_gateway", lambda self: True)
    monkeypatch.setattr(
        QwenCompatibleGateway,
        "_request_completion",
        lambda self, *, prompt: {
            "choices": [{"message": {"content": "这是来自远端模型网关的真实契约回答。"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21},
        },
    )
    original_generate_with_remote = QwenCompatibleGateway._generate_with_remote

    def generate_with_test_config(self, *, question, prompt, stream):
        previous_api_key = self.settings.chat_qwen_api_key
        object.__setattr__(self.settings, "chat_qwen_api_key", "test-api-key")
        try:
            return original_generate_with_remote(self, question=question, prompt=prompt, stream=stream)
        finally:
            object.__setattr__(self.settings, "chat_qwen_api_key", previous_api_key)

    monkeypatch.setattr(QwenCompatibleGateway, "_generate_with_remote", generate_with_test_config)
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-remote-user",
        "title": "远端网关测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-remote-user"}))
    answer = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": "chat-remote-user",
        "sessionId": session_id,
        "question": "请用一句话总结这次回答来源",
        "stream": True,
    }))
    assert answer["task"]["status"] == "completed"
    assert answer["task"]["answerText"] == "这是来自远端模型网关的真实契约回答。"
    assert answer["task"]["chunks"][-1]["isFinal"] is True
    usage = unwrap(client.get(f"/api/v1/sessions/{session_id}/usage", params={"userId": "chat-remote-user"}))
    assert usage["records"][-1]["providerName"] == "qwen-compatible"
    assert usage["records"][-1]["modelName"]


def test_qwen_gateway_reports_missing_runtime_config_outside_tests(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    settings = get_settings().model_copy(update={"chat_qwen_base_url": None, "chat_qwen_api_key": None})
    gateway = QwenCompatibleGateway(settings)
    try:
        gateway.generate(question="配置缺失", prompt=prompt_fixture(), stream=True, attempt=0)
    except NonRetryableChatError as exc:
        assert exc.code == "chat_config_missing"
        assert "模型未配置完成" in str(exc)
    else:
        raise AssertionError("Expected missing chat config to fail outside pytest synthetic mode.")


def test_qwen_gateway_classifies_provider_http_failures(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, status_code: int, body: dict | None = None) -> None:
            self.status_code = status_code
            self._body = body or {}

        def json(self) -> dict:
            return self._body

    class FakeClient:
        def __init__(self, response: FakeResponse | Exception) -> None:
            self.response = response

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, *_args, **_kwargs):
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

    settings = get_settings().model_copy(update={"chat_qwen_base_url": "https://provider.example/v1", "chat_qwen_api_key": "test-key"})
    cases = [
        (FakeResponse(401), NonRetryableChatError, "chat_provider_auth_failed"),
        (FakeResponse(403), NonRetryableChatError, "chat_provider_auth_failed"),
        (FakeResponse(429), RetryableChatError, "chat_provider_rate_limited"),
        (FakeResponse(503), RetryableChatError, "chat_provider_unavailable"),
        (httpx.ConnectError("offline"), RetryableChatError, "chat_provider_unavailable"),
    ]
    for response, error_type, code in cases:
        gateway = QwenCompatibleGateway(settings, http_client=FakeClient(response))
        try:
            gateway._request_completion(prompt=prompt_fixture())
        except error_type as exc:
            assert exc.code == code
        else:
            raise AssertionError(f"Expected {code} to be raised.")


def test_qwen_gateway_reports_invalid_provider_content(monkeypatch) -> None:
    monkeypatch.setattr(QwenCompatibleGateway, "_should_use_remote_gateway", lambda self: True)
    monkeypatch.setattr(QwenCompatibleGateway, "_request_completion", lambda self, *, prompt: {"choices": []})
    settings = get_settings().model_copy(update={"chat_qwen_base_url": "https://provider.example/v1", "chat_qwen_api_key": "test-key"})
    gateway = QwenCompatibleGateway(settings)
    try:
        gateway.generate(question="返回为空", prompt=prompt_fixture(), stream=True, attempt=0)
    except NonRetryableChatError as exc:
        assert exc.code == "chat_provider_invalid_response"
        assert "无效结果" in str(exc)
    else:
        raise AssertionError("Expected invalid provider content to fail.")


def test_live_answer_permanent_failure_returns_failed_status() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-fail-user",
        "title": "失败测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-fail-user"}))
    answer = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": "chat-fail-user",
        "sessionId": session_id,
        "question": "__permanent_fail__ 触发失败",
        "stream": True,
    }))
    assert answer["task"]["status"] == "failed"
    assert answer["task"]["errorCode"] == "forced_permanent_failure"


def test_live_answer_stream_emits_ordered_events_and_persists_completion() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-stream-user",
        "title": "流式回答测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-stream-user"}))
    with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
        "userId": "chat-stream-user",
        "sessionId": session_id,
        "question": "请流式回答一个项目亮点",
        "stream": True,
    }) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = parse_sse_events(response.read().decode("utf-8"))
    assert [event["type"] for event in events][0] == "task-started"
    chunk_events = [event for event in events if event["type"] == "chunk"]
    assert len(chunk_events) >= 2
    assert set(chunk_events[0]["timing"]) == {
        "serverAcceptedAtMs", "providerRequestAtMs", "providerFirstTokenAtMs", "firstVisibleAtMs", "sseYieldAtMs",
    }
    assert chunk_events[0]["timing"]["serverAcceptedAtMs"] <= chunk_events[0]["timing"]["providerRequestAtMs"]
    assert chunk_events[0]["timing"]["providerRequestAtMs"] <= chunk_events[0]["timing"]["firstVisibleAtMs"]
    assert chunk_events[0]["timing"]["firstVisibleAtMs"] <= chunk_events[0]["timing"]["sseYieldAtMs"]
    assert all("timing" not in event for event in chunk_events[1:])
    assert [event["chunk"]["sequence"] for event in chunk_events] == list(range(1, len(chunk_events) + 1))
    assert events[-1]["type"] == "completed"
    assert events[-1]["task"]["status"] == "completed"
    assert events[-1]["task"]["answerText"]
    persisted = unwrap(client.get(f"/api/v1/live-answer/tasks/{events[-1]['task']['taskId']}", params={"userId": "chat-stream-user"}))
    assert persisted["status"] == "completed"
    assert persisted["answerText"] == events[-1]["task"]["answerText"]
    session_events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "chat-stream-user"}))["events"]
    answer_events = [event for event in session_events if event["kind"] == "answer-task-updated"]
    assert answer_events[0]["payload"]["trigger"] == "manual"
    assert answer_events[-1]["payload"]["task"]["status"] == "completed"
    assert not any(event["kind"] == "answer-stream" for event in session_events)


def test_live_answer_startup_reuses_one_validated_session_snapshot(monkeypatch) -> None:
    from app.deps import chat_service as chat_service_dep

    user_id = "chat-startup-snapshot-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "启动快照测试"}))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    service = chat_service_dep()
    original_get_session = service.session_service.get_session
    calls = 0

    def counted_get_session(*, user_id: str, session_id: str):
        nonlocal calls
        calls += 1
        return original_get_session(user_id=user_id, session_id=session_id)

    monkeypatch.setattr(service.session_service, "get_session", counted_get_session)
    stream = service.stream_answer_question(user_id=user_id, session_id=session_id, question="如何降低快答首字延迟？")
    started = next(stream)

    assert started["type"] == "task-started"
    assert calls == 1
    context_entries = service.session_service.repository.list_context_entries(session_id=session_id)
    assert context_entries[-1].related_task_id == started["task"].task_id
    assert context_entries[-1].source_kind == "manual-input"

    outcome, _ = service.cancel_task(user_id=user_id, task_id=started["task"].task_id)
    assert outcome == "cancelled"
    assert list(stream)[0]["type"] == "cancelled"


def test_live_answer_prefetches_detail_retrieval_during_quick_generation(monkeypatch) -> None:
    from app.deps import chat_service as chat_service_dep

    service = chat_service_dep()
    timeline: dict[str, float] = {}

    def scripted_stream_generate(*, question, prompt, attempt):
        _ = attempt
        if prompt.prompt_config.template_id == "interview-chat-quick":
            yield ChatAnswerChunk(
                sequence=1,
                text=f"<normalized_question>{question}</normalized_question>先给结论。",
                is_final=False,
            )
            sleep(0.08)
            timeline["quick_completed"] = perf_counter()
            yield ChatAnswerChunk(sequence=2, text="再说明依据。", is_final=True)
            return
        yield ChatAnswerChunk(sequence=1, text="详细回答内容。", is_final=True)

    def delayed_retrieval(*, user_id, session, question):
        _ = user_id, session
        timeline["retrieval_started"] = perf_counter()
        sleep(0.04)
        timeline["retrieval_completed"] = perf_counter()
        return RetrievalContext(
            normalized_question=question,
            context_text="",
            chunks=[], candidate_count=0, final_count=0, strategy="filtered-first",
        )

    monkeypatch.setattr(service.llm_gateway, "stream_generate", scripted_stream_generate)
    monkeypatch.setattr(service, "_retrieve_context", delayed_retrieval)
    session = unwrap(client.post("/api/v1/sessions", json={"userId": "chat-prefetch-user", "title": "预取测试"}))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-prefetch-user"}))

    events = list(service.stream_answer_question(
        user_id="chat-prefetch-user", session_id=session_id, question="如何优化链路？"
    ))

    assert events[-1]["type"] == "completed"
    assert timeline["retrieval_started"] < timeline["quick_completed"]
    assert timeline["retrieval_completed"] <= timeline["quick_completed"]


def test_live_answer_stream_failure_preserves_partial_output() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-stream-fail-user",
        "title": "流式失败测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-stream-fail-user"}))
    with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
        "userId": "chat-stream-fail-user",
        "sessionId": session_id,
        "question": "__stream_fail_after_chunk__ 触发部分失败",
        "stream": True,
    }) as response:
        assert response.status_code == 200
        events = parse_sse_events(response.read().decode("utf-8"))
    assert any(event["type"] == "chunk" for event in events)
    assert events[-1]["type"] == "failed"
    assert events[-1]["task"]["status"] == "failed"
    assert events[-1]["partialText"] == "简单回答\n这是已经生成的部分回答。"


def test_live_answer_stream_cancellation_isolates_late_chunks() -> None:
    from app.deps import chat_service as chat_service_dep

    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-stream-cancel-user",
        "title": "流式取消测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-stream-cancel-user"}))
    service = chat_service_dep()
    stream = service.stream_answer_question(user_id="chat-stream-cancel-user", session_id=session_id, question="请生成随后取消的回答")
    started = next(stream)
    assert started["type"] == "task-started"
    task_id = started["task"].task_id
    outcome, cancelled = service.cancel_task(user_id="chat-stream-cancel-user", task_id=task_id)
    assert outcome == "cancelled"
    assert cancelled.status == "cancelled"
    remaining = list(stream)
    assert remaining[0]["type"] == "cancelled"
    persisted = service.get_task(user_id="chat-stream-cancel-user", task_id=task_id)
    assert persisted.status == "cancelled"
    assert persisted.answer_text == ""


def test_live_answer_stream_continues_quick_and_detail_length_truncation(monkeypatch) -> None:
    from app.deps import llm_gateway_port

    gateway = llm_gateway_port()

    def scripted_stream_generate(*, question, prompt, attempt):
        template_id = prompt.prompt_config.template_id
        if template_id == "interview-chat-quick":
            yield ChatAnswerChunk(
                sequence=1,
                text=f"<normalized_question>{question}</normalized_question>先确认延迟，",
                provider_finish_reason="length",
                is_final=True,
            )
        elif template_id == "interview-chat-continuation-quick":
            yield ChatAnswerChunk(sequence=1, text="再结合链路追踪定位瓶颈。", provider_finish_reason="stop", is_final=True)
        elif template_id == "interview-chat-detail":
            yield ChatAnswerChunk(sequence=1, text="详细说明先检查队列，", provider_finish_reason="length", is_final=True)
        elif template_id == "interview-chat-continuation-detail":
            yield ChatAnswerChunk(sequence=1, text="检查队列，再扩容消费者并限制重试。", provider_finish_reason="stop", is_final=True)
        else:
            raise AssertionError(template_id)

    monkeypatch.setattr(gateway, "stream_generate", scripted_stream_generate)
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-continuation-user",
        "title": "回答完整性测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-continuation-user"}))

    with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
        "userId": "chat-continuation-user",
        "sessionId": session_id,
        "question": "如何定位性能瓶颈？",
        "stream": True,
    }) as response:
        events = parse_sse_events(response.read().decode("utf-8"))

    assert events[-1]["type"] == "completed"
    answer_text = events[-1]["task"]["answerText"]
    assert "先确认延迟，再结合链路追踪定位瓶颈。" in answer_text
    assert "详细说明先检查队列，再扩容消费者并限制重试。" in answer_text
    assert answer_text.count("检查队列") == 1
    chunks = [event["chunk"] for event in events if event["type"] == "chunk"]
    assert [chunk["sequence"] for chunk in chunks] == list(range(1, len(chunks) + 1))


def test_live_answer_stream_exhausted_continuation_preserves_partial_and_fails(monkeypatch) -> None:
    from app.deps import chat_service as chat_service_dep, llm_gateway_port

    gateway = llm_gateway_port()
    service = chat_service_dep()
    monkeypatch.setattr(service.settings, "chat_continuation_max_attempts", 2)

    def scripted_stream_generate(*, question, prompt, attempt):
        template_id = prompt.prompt_config.template_id
        if template_id == "interview-chat-quick":
            yield ChatAnswerChunk(
                sequence=1,
                text=f"<normalized_question>{question}</normalized_question>回答开始，",
                provider_finish_reason="length",
                is_final=True,
            )
        elif template_id == "interview-chat-continuation-quick":
            yield ChatAnswerChunk(sequence=1, text="仍未结束，", provider_finish_reason="length", is_final=True)
        else:
            raise AssertionError(template_id)

    monkeypatch.setattr(gateway, "stream_generate", scripted_stream_generate)
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "chat-continuation-fail-user",
        "title": "回答续写失败测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "chat-continuation-fail-user"}))

    with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
        "userId": "chat-continuation-fail-user",
        "sessionId": session_id,
        "question": "请完整回答",
        "stream": True,
    }) as response:
        events = parse_sse_events(response.read().decode("utf-8"))

    assert events[-1]["type"] == "failed"
    assert events[-1]["errorCode"] == "chat_answer_incomplete"
    assert "仍未结束" in events[-1]["partialText"]
    assert not any(event["type"] == "completed" for event in events)


def test_ended_interview_review_returns_owned_chronological_dual_role_transcripts() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "review-transcript-owner",
        "title": "后端工程师一面",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "review-transcript-owner"}))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/context", json={
        "userId": "review-transcript-owner",
        "role": "interviewer",
        "sourceKind": "realtime-system",
        "content": "请介绍一下最近负责的项目。",
        "visibility": "session",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/context", json={
        "userId": "review-transcript-owner",
        "role": "candidate",
        "sourceKind": "realtime-microphone",
        "content": "我最近负责订单服务的稳定性建设。",
        "visibility": "session",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/context", json={
        "userId": "review-transcript-owner",
        "role": "candidate",
        "sourceKind": "realtime-interim",
        "content": "这是一条未确认的临时识别",
        "visibility": "session",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": "review-transcript-owner"}))

    review = unwrap(client.get(f"/api/v1/sessions/{session_id}/review", params={"userId": "review-transcript-owner"}))

    assert review["status"] == "ended"
    assert review["title"] == "后端工程师一面"
    assert review["durationMs"] >= 0
    assert [(item["role"], item["speakerLabel"], item["text"]) for item in review["transcripts"]] == [
        ("interviewer", "面试官", "请介绍一下最近负责的项目。"),
        ("candidate", "我", "我最近负责订单服务的稳定性建设。"),
    ]
    assert [item["ordering"] for item in review["transcripts"]] == sorted(item["ordering"] for item in review["transcripts"])

    forbidden = client.get(f"/api/v1/sessions/{session_id}/review", params={"userId": "different-review-user"})
    assert forbidden.status_code == 403
    assert "订单服务" not in forbidden.text

    unwrap(client.delete(f"/api/v1/sessions/{session_id}", params={"userId": "review-transcript-owner"}))
    deleted = client.get(f"/api/v1/sessions/{session_id}/review", params={"userId": "review-transcript-owner"})
    assert deleted.status_code == 404
    assert "订单服务" not in deleted.text


def test_live_interview_review_is_not_available_before_end() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "review-live-owner",
        "title": "尚未结束的面试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "review-live-owner"}))

    response = client.get(f"/api/v1/sessions/{session_id}/review", params={"userId": "review-live-owner"})

    assert response.status_code == 409
    assert "结束后" in response.text


def test_web_state_recent_interviews_are_limited_to_five_items() -> None:
    logged_in = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": "recent-user@example.com",
        "password": "Password123!",
        "displayName": "Recent User",
        "clientLabel": "recent-web",
    }))
    headers = {"Authorization": f"Bearer {logged_in['tokens']['accessToken']}"}
    for index in range(6):
        unwrap(client.post("/api/v1/sessions", json={
            "userId": logged_in["user"]["userId"],
            "title": f"最近面试 {index + 1}",
        }))
    state = unwrap(client.get("/api/v1/web/state", headers=headers))
    assert len(state["interviews"]) == 6
    assert state["interviews"][0]["title"] == "最近面试 6"
    assert state["interviews"][-1]["title"] == "最近面试 1"


def test_screenshot_answer_upload_validation_and_generation_flow() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "screenshot-user",
        "title": "截图回答测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "screenshot-user"}))

    invalid = client.post("/api/v1/screenshot-answer/upload-intents", json={
        "userId": "screenshot-user",
        "sessionId": session_id,
        "filename": "bad.gif",
        "contentType": "image/gif",
        "sizeBytes": 1024,
    })
    assert invalid.status_code == 400

    first_intent = unwrap(client.post("/api/v1/screenshot-answer/upload-intents", json={
        "userId": "screenshot-user",
        "sessionId": session_id,
        "filename": "system-design-1.png",
        "contentType": "image/png",
        "sizeBytes": 2048,
    }))
    second_intent = unwrap(client.post("/api/v1/screenshot-answer/upload-intents", json={
        "userId": "screenshot-user",
        "sessionId": session_id,
        "filename": "system-design-2.png",
        "contentType": "image/png",
        "sizeBytes": 2048,
    }))
    first_upload = unwrap(client.post("/api/v1/screenshot-answer/uploads/complete", json={
        "userId": "screenshot-user",
        "sessionId": session_id,
        "intentId": first_intent["intentId"],
        "objectKey": first_intent["objectKey"],
        "contentType": "image/png",
        "sizeBytes": 2048,
    }))
    second_upload = unwrap(client.post("/api/v1/screenshot-answer/uploads/complete", json={
        "userId": "screenshot-user",
        "sessionId": session_id,
        "intentId": second_intent["intentId"],
        "objectKey": second_intent["objectKey"],
        "contentType": "image/png",
        "sizeBytes": 2048,
    }))
    uploads = unwrap(client.get(f"/api/v1/screenshot-answer/sessions/{session_id}/uploads", params={"userId": "screenshot-user"}))
    assert len(uploads) == 2
    assert uploads[0]["imageId"] == first_upload["imageId"]

    answer = unwrap(client.post("/api/v1/screenshot-answer/tasks", json={
        "userId": "screenshot-user",
        "sessionId": session_id,
        "imageIds": [first_upload["imageId"], second_upload["imageId"]],
        "instruction": "请根据截图给出系统设计回答思路",
        "stream": True,
    }))
    assert answer["task"]["status"] == "completed"
    assert answer["task"]["imageCount"] == 2
    assert answer["task"]["visionProviderName"] == "qwen-vision-compatible"
    assert answer["task"]["providerName"] == "qwen-vision-compatible"
    assert answer["task"]["promptTemplateId"] == "screenshot-vision-direct"
    assert answer["task"]["retrievalExcerptCount"] == 0
    assert "```" in answer["task"]["answerText"]
    assert answer["task"]["chunks"][-1]["isFinal"] is True
    task = unwrap(client.get(f"/api/v1/screenshot-answer/tasks/{answer['task']['taskId']}", params={"userId": "screenshot-user"}))
    assert task["taskId"] == answer["task"]["taskId"]
    history = unwrap(client.get(f"/api/v1/screenshot-answer/sessions/{session_id}/history", params={"userId": "screenshot-user"}))
    assert len(history) >= 1
    context = unwrap(client.get(f"/api/v1/sessions/{session_id}/context", params={"userId": "screenshot-user"}))
    assert any(item["role"] == "screenshot" for item in context["entries"])
    assert any(item["role"] == "assistant" and item["sourceKind"] == "screenshot-answer" for item in context["entries"])
    usage = unwrap(client.get(f"/api/v1/sessions/{session_id}/usage", params={"userId": "screenshot-user"}))
    assert usage["totals"]["recordCount"] >= 1
    assert any(item["providerName"] == "qwen-vision-compatible" for item in usage["records"])


def test_screenshot_answer_retries_then_fails() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "screenshot-retry-user",
        "title": "截图重试测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "screenshot-retry-user"}))
    upload_intent = unwrap(client.post("/api/v1/screenshot-answer/upload-intents", json={
        "userId": "screenshot-retry-user",
        "sessionId": session_id,
        "filename": "retry-shot.png",
        "contentType": "image/png",
        "sizeBytes": 1024,
    }))
    upload = unwrap(client.post("/api/v1/screenshot-answer/uploads/complete", json={
        "userId": "screenshot-retry-user",
        "sessionId": session_id,
        "intentId": upload_intent["intentId"],
        "objectKey": upload_intent["objectKey"],
        "contentType": "image/png",
        "sizeBytes": 1024,
    }))
    retried = unwrap(client.post("/api/v1/screenshot-answer/tasks", json={
        "userId": "screenshot-retry-user",
        "sessionId": session_id,
        "imageIds": [upload["imageId"]],
        "instruction": "__retry_once__ 请根据截图回答",
        "stream": True,
    }))
    assert retried["task"]["status"] == "completed"
    assert retried["task"]["retryCount"] == 1

    failed_upload_intent = unwrap(client.post("/api/v1/screenshot-answer/upload-intents", json={
        "userId": "screenshot-retry-user",
        "sessionId": session_id,
        "filename": "permanent-fail-shot.png",
        "contentType": "image/png",
        "sizeBytes": 1024,
    }))
    failed_upload = unwrap(client.post("/api/v1/screenshot-answer/uploads/complete", json={
        "userId": "screenshot-retry-user",
        "sessionId": session_id,
        "intentId": failed_upload_intent["intentId"],
        "objectKey": failed_upload_intent["objectKey"],
        "contentType": "image/png",
        "sizeBytes": 1024,
    }))
    failed = unwrap(client.post("/api/v1/screenshot-answer/tasks", json={
        "userId": "screenshot-retry-user",
        "sessionId": session_id,
        "imageIds": [failed_upload["imageId"]],
        "instruction": "__permanent_fail__ 触发视觉失败",
        "stream": True,
    }))
    assert failed["task"]["status"] == "failed"
    assert failed["task"]["errorCode"] == "NonRetryableVisionError"


def test_remote_screenshot_capture_request_runs_through_bound_desktop_device() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "remote-screenshot-user",
        "title": "远程截屏回答测试",
    }))
    session_id = session["sessionId"]

    registered = unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-remote-shot",
        "manualCode": "998877",
        "displayName": "面试稳伴随程序 · Mac",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }))
    assert registered["manualCode"] == "998877"

    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "remote-screenshot-user",
        "manualCode": "998877",
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "remote-screenshot-user",
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "remote-screenshot-user"}))

    created = unwrap(client.post(f"/api/v1/screenshot-answer/sessions/{session_id}/remote-capture-requests", json={
        "userId": "remote-screenshot-user",
        "instruction": "请根据当前屏幕里的系统设计题给出回答",
    }))
    assert created["status"] == "requested"
    assert created["deviceId"] == "device-remote-shot"

    pending_requests = unwrap(client.get(
        f"/api/v1/screenshot-answer/sessions/{session_id}/remote-capture-requests",
        params={"userId": "remote-screenshot-user"},
    ))
    assert len(pending_requests) == 1
    assert pending_requests[0]["requestId"] == created["requestId"]
    assert pending_requests[0]["status"] == "requested"
    assert pending_requests[0]["answerTask"] is None

    queued = unwrap(client.get("/api/v1/screenshot-answer/desktop-devices/device-remote-shot/capture-requests/next", params={
        "manualCode": "998877",
    }))
    assert queued is not None
    assert queued["requestId"] == created["requestId"]

    png_payload = Path(__file__).resolve().parents[2].joinpath("web/public/assets/brand/favicon.png").read_bytes()
    uploaded = unwrap(client.post(
        f"/api/v1/screenshot-answer/capture-requests/{created['requestId']}/desktop-upload",
        data={"deviceId": "device-remote-shot", "manualCode": "998877"},
        files={"screenshot": ("current-screen.png", png_payload, "image/png")},
    ))
    assert uploaded["status"] in {"processing", "completed"}

    loaded = unwrap(client.get(f"/api/v1/screenshot-answer/capture-requests/{created['requestId']}", params={
        "userId": "remote-screenshot-user",
    }))
    assert loaded["status"] == "completed"
    assert loaded["capturedFilename"] == "current-screen.png"
    assert loaded["answerTask"] is not None
    assert loaded["answerTask"]["status"] == "completed"
    assert loaded["answerTask"]["visionProviderName"] == "qwen-vision-compatible"
    assert loaded["answerTaskId"] == loaded["answerTask"]["taskId"]

    completed_requests = unwrap(client.get(
        f"/api/v1/screenshot-answer/sessions/{session_id}/remote-capture-requests",
        params={"userId": "remote-screenshot-user"},
    ))
    assert len(completed_requests) == 1
    assert completed_requests[0]["status"] == "completed"
    assert completed_requests[0]["answerTask"]["taskId"] == loaded["answerTask"]["taskId"]

    history = unwrap(client.get(f"/api/v1/screenshot-answer/sessions/{session_id}/history", params={
        "userId": "remote-screenshot-user",
    }))
    assert any(item["taskId"] == loaded["answerTask"]["taskId"] for item in history)
    session_events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "remote-screenshot-user"}))["events"]
    capture_events = [event for event in session_events if event["kind"] == "screenshot-capture-updated"]
    assert [event["payload"]["stage"] for event in capture_events] == ["requested", "claimed", "uploaded", "vision-running", "completed"]
    assert capture_events[-1]["payload"]["answerTask"]["status"] == "completed"
    assert all("manualCode" not in event["payload"] and "screenshot" not in event["payload"] for event in capture_events)


def test_desktop_shortcut_capture_publishes_realtime_acceptance_once() -> None:
    user_id = "shortcut-feedback-user"
    device_id = "device-shortcut-feedback"
    manual_code = "887766"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "快捷键即时反馈"}))
    session_id = session["sessionId"]
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": device_id,
        "manualCode": manual_code,
        "displayName": "面试稳伴随程序 · Mac",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }))
    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": user_id,
        "manualCode": manual_code,
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": user_id,
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

    created = unwrap(client.post(
        f"/api/v1/screenshot-answer/desktop-devices/{device_id}/shortcut-capture-requests",
        json={"deviceId": device_id, "manualCode": manual_code},
    ))
    events = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/events",
        params={"userId": user_id},
    ))["events"]
    accepted = [event for event in events if event["kind"] == "screenshot-shortcut-accepted"]
    assert len(accepted) == 1
    assert accepted[0]["payload"] == {"requestId": created["requestId"], "status": "requested"}

    duplicate = client.post(
        f"/api/v1/screenshot-answer/desktop-devices/{device_id}/shortcut-capture-requests",
        json={"deviceId": device_id, "manualCode": manual_code},
    )
    assert duplicate.status_code == 409
    events_after_rejection = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/events",
        params={"userId": user_id},
    ))["events"]
    assert len([event for event in events_after_rejection if event["kind"] == "screenshot-shortcut-accepted"]) == 1


def test_remote_screenshot_capture_request_requires_active_desktop_binding() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "remote-screenshot-no-binding-user",
        "title": "未绑定桌面端截屏测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "remote-screenshot-no-binding-user"}))

    response = client.post(f"/api/v1/screenshot-answer/sessions/{session_id}/remote-capture-requests", json={
        "userId": "remote-screenshot-no-binding-user",
        "instruction": "请根据当前屏幕回答",
    })
    assert response.status_code == 404


def test_remote_screenshot_idle_poll_returns_null_without_mutating_state() -> None:
    unregistered = client.get(
        "/api/v1/screenshot-answer/desktop-devices/device-idle-unregistered/capture-requests/next",
        params={"manualCode": "654321"},
    )
    assert unregistered.status_code == 200
    assert unwrap(unregistered) is None

    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-idle-registered",
        "manualCode": "654322",
        "displayName": "空闲轮询测试设备",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }))
    before = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/pairing-status",
        params={"manualCode": "654322", "deviceId": "device-idle-registered"},
    ))
    idle = client.get(
        "/api/v1/screenshot-answer/desktop-devices/device-idle-registered/capture-requests/next",
        params={"manualCode": "654322"},
    )
    after = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/pairing-status",
        params={"manualCode": "654322", "deviceId": "device-idle-registered"},
    ))

    assert idle.status_code == 200
    assert unwrap(idle) is None
    assert before == after
    assert before["state"] == "registered"
    assert before["bound"] is False


def test_remote_screenshot_idle_compatibility_does_not_relax_upload_authorization() -> None:
    response = client.post(
        "/api/v1/screenshot-answer/capture-requests/nonexistent-request/desktop-upload",
        data={"deviceId": "unknown-device", "manualCode": "654323"},
        files={"screenshot": ("synthetic.png", b"synthetic", "image/png")},
    )
    assert response.status_code == 404


def test_remote_screenshot_capture_request_can_be_cancelled_before_desktop_upload() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "remote-screenshot-cancel-user",
        "title": "远程截屏终止测试",
    }))
    session_id = session["sessionId"]

    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-remote-cancel",
        "manualCode": "112233",
        "displayName": "面试稳伴随程序 · Mac",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }))
    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "remote-screenshot-cancel-user",
        "manualCode": "112233",
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "remote-screenshot-cancel-user",
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "remote-screenshot-cancel-user"}))

    created = unwrap(client.post(f"/api/v1/screenshot-answer/sessions/{session_id}/remote-capture-requests", json={
        "userId": "remote-screenshot-cancel-user",
        "instruction": "请根据当前屏幕里的代码题给出回答",
    }))
    cancelled = unwrap(client.post(f"/api/v1/screenshot-answer/capture-requests/{created['requestId']}/cancel", json={
        "userId": "remote-screenshot-cancel-user",
    }))
    assert cancelled["status"] == "cancelled"

    queued = unwrap(client.get("/api/v1/screenshot-answer/desktop-devices/device-remote-cancel/capture-requests/next", params={
        "manualCode": "112233",
    }))
    assert queued is None


def test_realtime_speech_websocket_detects_question_without_generating_answer() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "realtime-user",
        "title": "实时语音测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "realtime-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-user",
        "sessionId": session_id,
        "sourceKind": "system",
        "clientName": "desktop-companion",
    }))

    question_text = "介绍一下你最近做的项目"
    payload = base64.b64encode(question_text.encode("utf-8")).decode("utf-8")
    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={publisher['token']}") as websocket:
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-realtime-1",
            "sourceId": "system-loopback",
            "sequence": 0,
            "sourceKind": "system",
            "segmentId": "seg-system-1",
            "revision": 1,
            "capturedAtMs": 1000,
            "startedAtMs": 1000,
            "endedAtMs": 3000,
            "durationMs": 2000,
            "codec": "opus",
            "sampleRateHz": 48000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": payload,
        })
        first = websocket.receive_json()
        second = websocket.receive_json()

    assert first["kind"] == "transcript-updated"
    assert first["payload"]["role"] == "interviewer"
    assert second["kind"] == "question-confirmed"
    assert second["payload"]["text"] == question_text
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "realtime-user"}))
    assert runtime["transcriptCount"] == 1
    assert runtime["questionCandidateCount"] == 1
    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "realtime-user"}))
    assert transcripts["transcripts"][0]["text"] == question_text
    candidates = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/question-candidates", params={"userId": "realtime-user"}))
    assert candidates["candidates"][0]["state"] == "confirmed"
    assert candidates["candidates"][0]["answerTaskId"] is None
    history = unwrap(client.get(f"/api/v1/live-answer/sessions/{session_id}/history", params={"userId": "realtime-user"}))
    assert history == []
    context = unwrap(client.get(f"/api/v1/sessions/{session_id}/context", params={"userId": "realtime-user"}))
    assert any(item["role"] == "interviewer" and item["content"] == question_text for item in context["entries"])
    assert not any(item["role"] == "assistant" for item in context["entries"])
    usage = unwrap(client.get(f"/api/v1/sessions/{session_id}/usage", params={"userId": "realtime-user"}))
    assert any(item["providerName"] == "qwen-realtime-asr-compatible" for item in usage["records"])
    events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "realtime-user"}))
    assert not any(item["kind"] == "answer-stream" for item in events["events"])


def test_provider_partial_is_published_without_waiting_for_another_audio_frame() -> None:
    user_id = "receiver-partial-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "接收线程 Partial 测试"}))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "system",
        "clientName": "desktop-receiver-partial",
    }))
    now_ms = int(time() * 1000)
    frame = AudioFrame(
        publisher_id=publisher["publisherId"],
        session_id=session_id,
        device_id="receiver-partial-device",
        source_id="system-loopback",
        source_kind="system",
        segment_id="receiver-partial-segment",
        revision=3,
        sequence=2,
        captured_at_ms=now_ms - 80,
        started_at_ms=now_ms - 180,
        ended_at_ms=now_ms,
        duration_ms=180,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=False,
        audio_bytes=b"synthetic-pcm",
        trace_id="trace-receiver-partial",
        sent_at_ms=now_ms - 60,
        vad_triggered_at_ms=now_ms - 180,
        speech_confirmed_at_ms=now_ms - 140,
        backend_received_at_ms=now_ms - 50,
    )
    realtime_speech_service()._publish_provider_partial(frame, TranscriptResult(
        text="请介绍你的项目经历",
        confidence=0.82,
        partial_received_at_ms=now_ms - 5,
        audio_appended_at_ms=now_ms - 45,
    ))

    events = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/events",
        params={"userId": user_id},
    ))["events"]
    partial = next(item for item in events if item["kind"] == "transcript-updated")
    assert partial["payload"]["text"] == "请介绍你的项目经历"
    assert partial["payload"]["performance"]["qwenPartialReceivedAtMs"] == now_ms - 5
    assert partial["payload"]["performance"]["redisEventXaddAtMs"] >= now_ms - 5
    assert partial["payload"]["performance"]["framesBeforeFirstPartial"] == 3
    assert partial["payload"]["performance"]["systemVadTriggerAtMs"] == now_ms - 180
    assert partial["payload"]["performance"]["systemSpeechStartAtMs"] == now_ms - 140


def test_realtime_question_confirmation_does_not_start_answer() -> None:
    service = realtime_speech_service()
    assert not hasattr(service, "_start_automatic_answer")
    assert not hasattr(service, "_answer_executor")
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "realtime-nonblocking-user",
        "title": "实时回答不阻塞收音测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "realtime-nonblocking-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-nonblocking-user",
        "sessionId": session_id,
        "sourceKind": "system",
        "clientName": "desktop-companion",
    }))
    payload = base64.b64encode("请介绍一个最近的项目".encode("utf-8")).decode("utf-8")

    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={publisher['token']}") as websocket:
        websocket.send_json({
            "type": "audio-frame", "deviceId": "device-realtime-nonblocking",
            "sourceId": "system-loopback", "sequence": 0, "sourceKind": "system",
            "segmentId": "seg-system-nonblocking", "revision": 1,
            "capturedAtMs": 1000, "startedAtMs": 1000, "endedAtMs": 3000,
            "durationMs": 2000, "codec": "opus", "sampleRateHz": 48000,
            "channels": 1, "isFinal": True, "audioBase64": payload,
        })
        assert websocket.receive_json()["kind"] == "transcript-updated"
        assert websocket.receive_json()["kind"] == "question-confirmed"
    candidate = service.list_candidates(user_id="realtime-nonblocking-user", session_id=session_id).candidates[0]
    assert candidate.state == "confirmed"
    assert candidate.answer_task_id is None
    event_kinds = [event.kind for event in service.list_events(user_id="realtime-nonblocking-user", session_id=session_id).events]
    assert "question-confirmed" in event_kinds
    assert "answer-task-updated" not in event_kinds


def test_realtime_speech_websocket_reports_asr_degraded_without_closing_stream() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "realtime-recover-user",
        "title": "实时语音失败恢复测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "realtime-recover-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-recover-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "desktop-companion",
    }))

    failed_payload = base64.b64encode("__asr_fail__".encode("utf-8")).decode("utf-8")
    recovered_text = "我正在介绍项目背景"
    recovered_payload = base64.b64encode(recovered_text.encode("utf-8")).decode("utf-8")
    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={publisher['token']}") as websocket:
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-realtime-recover",
            "sourceId": "mic-default",
            "sourceKind": "microphone",
            "sequence": 1,
            "segmentId": "seg-mic-failed",
            "revision": 1,
            "capturedAtMs": 1000,
            "startedAtMs": 1000,
            "endedAtMs": 1500,
            "durationMs": 500,
            "codec": "opus",
            "sampleRateHz": 48000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": failed_payload,
        })
        degraded = websocket.receive_json()
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-realtime-recover",
            "sourceId": "mic-default",
            "sequence": 2,
            "sourceKind": "microphone",
            "sequence": 2,
            "segmentId": "seg-mic-recovered",
            "revision": 1,
            "capturedAtMs": 1600,
            "startedAtMs": 1600,
            "endedAtMs": 2600,
            "durationMs": 1000,
            "codec": "opus",
            "sampleRateHz": 48000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": recovered_payload,
        })
        recovered = websocket.receive_json()

    assert degraded["kind"] == "degraded"
    assert degraded["payload"]["reason"] == "asr-frame-failed"
    assert recovered["kind"] == "transcript-updated"
    assert recovered["payload"]["role"] == "candidate"
    assert recovered["payload"]["text"] == recovered_text


def test_realtime_http_frame_ingest_returns_before_transcript_persists() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "realtime-http-user",
        "title": "实时 HTTP 收音测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "realtime-http-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-http-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "desktop-http-companion",
    }))

    payload = base64.b64encode("我正在通过 HTTP 路径测试实时语音".encode("utf-8")).decode("utf-8")
    ingest = unwrap(client.post("/api/v1/realtime-speech/frames", json={
        "type": "audio-frame",
        "token": publisher["token"],
        "deviceId": "device-http-1",
        "sourceId": "mic-default",
        "sequence": 1,
        "sourceKind": "microphone",
        "segmentId": "seg-http-1",
        "revision": 1,
        "capturedAtMs": 1000,
        "startedAtMs": 1000,
        "endedAtMs": 1800,
        "durationMs": 800,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": True,
        "audioBase64": payload,
    }))
    assert ingest == []

    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "realtime-http-user"}))
        if transcripts["transcripts"]:
            assert transcripts["transcripts"][0]["text"] == "我正在通过 HTTP 路径测试实时语音"
            break
        sleep(0.05)
    else:
        raise AssertionError("HTTP ingest worker did not persist transcript in time")


def test_realtime_ingest_websocket_acknowledges_immediately_and_persists_transcript() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "realtime-ingest-ws-user",
        "title": "实时 WebSocket 收音测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "realtime-ingest-ws-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-ingest-ws-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "desktop-ws-companion",
    }))

    payload = base64.b64encode("我正在通过长连接测试实时语音".encode("utf-8")).decode("utf-8")
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}") as websocket:
        connected = websocket.receive_json()
        assert connected["kind"] == "connection-state"
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-ws-1",
            "sourceId": "mic-default",
            "sequence": 1,
            "sourceKind": "microphone",
            "segmentId": "seg-ws-1",
            "revision": 1,
            "capturedAtMs": 1000,
            "sentAtMs": 1010,
            "traceId": "trace-ingest-ws-1",
            "sequence": 0,
            "startedAtMs": 1000,
            "endedAtMs": 1800,
            "durationMs": 800,
            "codec": "pcm-s16le",
            "sampleRateHz": 16000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": payload,
        })
        accepted = websocket.receive_json()
        assert accepted["kind"] == "frame-accepted"
        assert accepted["payload"]["sequence"] == 0
        assert accepted["payload"]["traceId"] == "trace-ingest-ws-1"

    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "realtime-ingest-ws-user"}))
        if transcripts["transcripts"]:
            assert transcripts["transcripts"][0]["text"] == "我正在通过长连接测试实时语音"
            assert transcripts["transcripts"][0]["performance"]["traceId"] == "trace-ingest-ws-1"
            break
        sleep(0.05)
    else:
        raise AssertionError("ingest websocket worker did not persist transcript in time")


def test_realtime_ingest_websocket_closes_a_sequence_gap_storm() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "realtime-gap-storm-user",
        "title": "实时序列缺口熔断测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "realtime-gap-storm-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-gap-storm-user",
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "synthetic-gap-storm-client",
    }))
    frame = {
        "type": "audio-frame",
        "deviceId": "synthetic-device",
        "sourceId": "synthetic-mic",
        "sequence": 1,
        "sourceKind": "microphone",
        "segmentId": "synthetic-segment",
        "revision": 1,
        "capturedAtMs": 1000,
        "startedAtMs": 1000,
        "endedAtMs": 1020,
        "durationMs": 20,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": False,
        "audioBase64": base64.b64encode(b"synthetic-audio").decode("utf-8"),
    }

    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}") as websocket:
        assert websocket.receive_json()["kind"] == "connection-state"
        for _ in range(7):
            websocket.send_json(frame)
            gap = websocket.receive_json()
            assert gap["kind"] == "sequence-gap"
            assert gap["payload"]["expected"] == 0
        websocket.send_json(frame)
        degraded = websocket.receive_json()
        assert degraded["kind"] == "degraded"
        assert degraded["payload"] == {
            "reason": "sequence-gap-budget-exhausted",
            "sourceKind": "microphone",
            "expected": 0,
            "received": 1,
            "gapEvents": 8,
            "retryable": True,
        }


def test_dashscope_gateway_prefers_workspace_specific_endpoint() -> None:
    settings = Settings(
        realtime_asr_workspace_id="ws-rhhabbnvh2rsbkj2",
        realtime_asr_workspace_region="cn-beijing",
        realtime_asr_ws_url="wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        realtime_asr_model="qwen3-asr-flash-realtime-2026-02-10",
    )
    gateway = DashScopeRealtimeAsrGateway(settings, logging.getLogger("test"))
    assert gateway._connect_url() == (
        "wss://ws-rhhabbnvh2rsbkj2.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime"
        "?model=qwen3-asr-flash-realtime-2026-02-10"
    )


def test_dashscope_gateway_reuses_source_session_and_waits_for_session_created(monkeypatch) -> None:
    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[str] = []
            self._events = [{"type": "session.created", "session": {"id": "sess-1"}}]
            self._segment = 0

        def recv(self, timeout=None):  # noqa: ANN001
            import json
            if not self._events:
                raise TimeoutError()
            return json.dumps(self._events.pop(0), ensure_ascii=False)

        def send(self, payload: str) -> None:
            self.sent.append(payload)
            if "input_audio_buffer.append" in payload:
                self._segment += 1
                self._events.append({
                    "type": "conversation.item.input_audio_transcription.text",
                    "text": "第一段 interim" if self._segment == 1 else "第二段 interim",
                })
            if "input_audio_buffer.commit" in payload:
                self._events.append({
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "第一段 final" if self._segment == 1 else "第二段 final",
                })

        def close(self) -> None:
            return None

    fake_connections: list[FakeWebSocket] = []

    def fake_connect(*args, **kwargs):  # noqa: ANN002, ANN003
        websocket = FakeWebSocket()
        fake_connections.append(websocket)
        return websocket

    monkeypatch.setattr("app.services.dashscope_realtime_asr_gateway.connect", fake_connect)
    settings = Settings(
        realtime_asr_api_key="test-key",
        realtime_asr_model="qwen3-asr-flash-realtime-2026-02-10",
    )
    gateway = DashScopeRealtimeAsrGateway(settings, logging.getLogger("test"))

    frame_one = AudioFrame(
        publisher_id="pub-1",
        session_id="session-1",
        device_id="device-1",
        source_id="mic-default",
        source_kind="microphone",
        segment_id="seg-1",
        revision=1,
        sequence=1,
        captured_at_ms=1,
        started_at_ms=1,
        ended_at_ms=200,
        duration_ms=199,
        codec="pcm-s16le",
        sample_rate_hz=16000,
        channels=1,
        is_final=True,
        audio_bytes=b"hello-one",
    )
    frame_two = AudioFrame(
        publisher_id="pub-1",
        session_id="session-1",
        device_id="device-1",
        source_id="mic-default",
        source_kind="microphone",
        segment_id="seg-2",
        revision=1,
        sequence=2,
        captured_at_ms=201,
        started_at_ms=201,
        ended_at_ms=360,
        duration_ms=159,
        codec="pcm-s16le",
        sample_rate_hz=16000,
        channels=1,
        is_final=True,
        audio_bytes=b"hello-two",
        source_generation=2,
    )

    first = gateway.transcribe(frame=frame_one, attempt=0)
    second = gateway.transcribe(frame=frame_two, attempt=0)

    assert first.text == "第一段 final"
    assert second.text == "第二段 final"
    assert len(fake_connections) == 1
    assert gateway.diagnostics("microphone")["connection_recreations"] == 1
    assert gateway.diagnostics("microphone")["asr_connection_create_count"] == 1
    assert gateway.diagnostics("microphone")["asr_connection_reconnect_count"] == 0
    assert gateway.diagnostics("microphone")["utterance_count"] == 2
    assert gateway.diagnostics("microphone")["utterances_per_connection"] == 2.0
    assert gateway.runtime_status("microphone")["mode"] == "manual"
    sent_payloads = "".join(fake_connections[0].sent)
    assert "session.update" in sent_payloads
    assert "input_audio_buffer.append" in sent_payloads
    assert "input_audio_buffer.commit" in sent_payloads


def test_desktop_machine_code_registers_and_binds_to_interview_session() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "desktop-binding-user",
        "title": "机器码绑定测试",
    }))
    session_id = session["sessionId"]

    missing = client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "desktop-binding-user",
        "manualCode": "654321",
    })
    assert missing.status_code == 404

    registered = unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-stable-mac",
        "manualCode": "654321",
        "displayName": "面试稳伴随程序 · Mac",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }))
    assert registered["status"] == "online"

    registered_status = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "654321",
        "deviceId": "device-stable-mac",
    }))
    assert registered_status["state"] == "registered"
    assert registered_status["registered"] is True
    assert registered_status["bound"] is False
    assert registered_status["devicePresence"] == "online"
    assert registered_status["sessionConnection"] == "idle"
    assert registered_status["permissionStatus"]["microphone"] is True

    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "desktop-binding-user",
        "manualCode": "654321",
    }))
    assert binding["deviceId"] == "device-stable-mac"
    assert binding["manualCode"] == "654321"
    assert binding["capabilities"]["screenCapture"] is True
    assert binding["accountBound"] is True
    assert binding["sessionConnection"] == "connected"

    duplicate_binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "desktop-binding-user",
        "manualCode": "654321",
    }))
    assert duplicate_binding["bindingId"] == binding["bindingId"]

    loaded = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", params={"userId": "desktop-binding-user"}))
    assert loaded["bindingId"] == binding["bindingId"]

    stale_status = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "654321",
        "deviceId": "device-stable-mac",
    }))
    assert stale_status["state"] == "bound"
    assert stale_status["bound"] is True

    bound_before_web_heartbeat = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/device-stable-mac/binding",
        params={"manualCode": "654321"},
    ))
    assert bound_before_web_heartbeat["sessionId"] == session_id

    heartbeat = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "desktop-binding-user",
        "bindingId": binding["bindingId"],
        "page": "preparation",
    }))
    assert heartbeat["page"] == "preparation"

    active = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/device-stable-mac/binding", params={"manualCode": "654321"}))
    assert active["sessionId"] == session_id
    assert active["ownerUserId"] == "desktop-binding-user"

    recovered_active = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/device-after-reinstall/binding", params={"manualCode": "654321"}))
    assert recovered_active["sessionId"] == session_id
    assert recovered_active["manualCode"] == "654321"
    code_active = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/by-code/654321/binding"))
    assert code_active["sessionId"] == session_id
    assert code_active["deviceId"] == "device-stable-mac"
    bound_status = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "654321",
        "deviceId": "device-stable-mac",
    }))
    assert bound_status["state"] == "bound"
    assert bound_status["bound"] is True
    assert bound_status["sessionStatus"] == "preparing"
    assert bound_status["binding"]["sessionId"] == session_id

    next_session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "desktop-binding-user",
        "title": "新的机器码绑定测试",
    }))
    next_binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{next_session['sessionId']}/desktop-binding", json={
        "userId": "desktop-binding-user",
        "manualCode": "654321",
    }))
    assert next_binding["status"] == "bound"
    assert next_binding["sessionId"] == next_session["sessionId"]
    previous_binding = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding",
        params={"userId": "desktop-binding-user"},
    ))
    assert previous_binding["status"] == "stale"
    current_binding = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/device-stable-mac/binding",
        params={"manualCode": "654321"},
    ))
    assert current_binding["sessionId"] == next_session["sessionId"]

    next_device = unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-new-generation",
        "manualCode": "654321",
        "displayName": "面试稳伴随程序 · New Mac",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }))
    assert next_device["generation"] > registered["generation"]
    generation_status = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "654321",
        "deviceId": "device-new-generation",
    }))
    assert generation_status["state"] == "stale-bound"
    assert generation_status["staleReason"] == "desktop-generation-changed"

    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "desktop-binding-user",
        "manualCode": "654321",
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "desktop-binding-user",
        "bindingId": binding["bindingId"],
        "page": "preparation",
    }))

    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "desktop-binding-user"}))
    live_status = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "654321",
        "deviceId": "device-new-generation",
    }))
    assert live_status["state"] == "bound"
    assert live_status["sessionStatus"] == "live"
    active_connection = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/device-new-generation/active-connection",
        params={"manualCode": "654321"},
    ))
    assert active_connection["authoritative"] is True
    assert active_connection["binding"]["sessionId"] == session_id
    assert active_connection["leaseVersion"].startswith(binding["bindingId"])
    assert active_connection["refreshAfterMs"] == 1000

    status = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/device-status", json={
        "deviceId": "device-new-generation",
        "manualCode": "654321",
        "captureState": "capturing",
        "sourceHealth": [
            {"sourceId": "mic-default", "sourceKind": "microphone", "label": "Mac 麦克风", "state": "silent", "stage": "track-live", "level": 0},
            {"sourceId": "system-loopback", "sourceKind": "system", "label": "系统音频", "state": "silent", "stage": "track-live", "level": 0},
        ],
        "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": True},
    }))
    assert status["kind"] == "device-status"
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "desktop-binding-user"}))
    assert runtime["deviceRegistered"] is True
    assert runtime["machineCodeBound"] is True
    assert runtime["sessionLive"] is True
    assert runtime["manualCode"] == "654321"
    assert runtime["sourceHealth"][0]["stage"] == "track-live"

    unwrap(client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": "desktop-binding-user"}))
    ended_status = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "654321",
        "deviceId": "device-new-generation",
    }))
    assert ended_status["state"] == "stale-bound"
    assert ended_status["staleReason"] == "session-not-active"


def test_new_device_binding_becomes_the_users_only_active_realtime_interview() -> None:
    first = unwrap(client.post("/api/v1/sessions", json={
        "userId": "single-live-user",
        "title": "第一场实时面试",
    }))
    second = unwrap(client.post("/api/v1/sessions", json={
        "userId": "single-live-user",
        "title": "第二场实时面试",
    }))
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "single-live-device-a",
        "manualCode": "310001",
        "displayName": "第一台 Mac",
        "capabilities": {"microphone": True, "systemAudio": True},
    }))
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "single-live-device-b",
        "manualCode": "310002",
        "displayName": "第二台 Mac",
        "capabilities": {"microphone": True, "systemAudio": True},
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{first['sessionId']}/desktop-binding", json={
        "userId": "single-live-user",
        "manualCode": "310001",
    }))
    unwrap(client.post(f"/api/v1/sessions/{first['sessionId']}/start", json={"userId": "single-live-user"}))
    first_publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "single-live-user",
        "sessionId": first["sessionId"],
        "sourceKind": "microphone",
        "clientName": "first-publisher",
    }))

    conflict = client.post(f"/api/v1/realtime-speech/sessions/{second['sessionId']}/desktop-binding", json={
        "userId": "single-live-user",
        "manualCode": "310002",
    })
    assert conflict.status_code == 409
    superseded = unwrap(client.post(f"/api/v1/sessions/{second['sessionId']}/supersede-active", json={
        "userId": "single-live-user",
        "expectedPreviousSessionId": first["sessionId"],
    }))
    assert superseded["retiredSessionIds"] == [first["sessionId"]]
    second_binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{second['sessionId']}/desktop-binding", json={
        "userId": "single-live-user",
        "manualCode": "310002",
    }))

    assert second_binding["status"] == "bound"
    previous_binding = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{first['sessionId']}/desktop-binding",
        params={"userId": "single-live-user"},
    ))
    assert previous_binding["status"] == "stale"
    previous_runtime = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{first['sessionId']}/runtime",
        params={"userId": "single-live-user"},
    ))
    assert next(item for item in previous_runtime["publishers"] if item["publisherId"] == first_publisher["publisherId"])["status"] == "closed"
    recent = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/last-used",
        params={"userId": "single-live-user"},
    ))
    assert recent["deviceId"] == "single-live-device-b"
    assert recent["maskedManualCode"] == "••••02"
    assert recent["accountBound"] is True
    assert recent["devicePresence"] == "online"
    assert recent["permissionStatus"]["microphone"] is True
    reused = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{second['sessionId']}/desktop-binding", json={
        "userId": "single-live-user",
        "reuseLastDevice": True,
    }))
    assert reused["deviceId"] == "single-live-device-b"

    current_connection = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/single-live-device-b/active-connection",
        params={"manualCode": "310002"},
    ))
    assert current_connection["binding"]["sessionId"] == second["sessionId"]
    assert current_connection["leaseVersion"].startswith(reused["bindingId"])
    stale_stream = client.get(
        f"/api/v1/realtime-speech/sessions/{first['sessionId']}/stream",
        params={"userId": "single-live-user"},
    )
    assert stale_stream.status_code == 410


def test_live_desktop_binding_is_pinned_and_cannot_be_taken_over_by_another_account() -> None:
    owner_session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "live-device-owner",
        "title": "正在使用设备的面试",
    }))
    challenger_session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "live-device-challenger",
        "title": "试图抢占设备的面试",
    }))
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "pinned-live-device",
        "manualCode": "318765",
        "displayName": "Pinned Live Mac",
        "capabilities": {"microphone": True, "systemAudio": True},
    }))
    owner_binding = unwrap(client.post(
        f"/api/v1/realtime-speech/sessions/{owner_session['sessionId']}/desktop-binding",
        json={"userId": "live-device-owner", "manualCode": "318765"},
    ))
    unwrap(client.post(
        f"/api/v1/sessions/{owner_session['sessionId']}/start",
        json={"userId": "live-device-owner"},
    ))

    pinned = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/pinned-live-device/active-connection",
        params={
            "manualCode": "318765",
            "pinnedSessionId": owner_session["sessionId"],
            "pinnedBindingId": owner_binding["bindingId"],
        },
    ))
    assert pinned["bindingLockState"] == "held"
    assert pinned["binding"]["sessionId"] == owner_session["sessionId"]
    assert pinned["binding"]["bindingId"] == owner_binding["bindingId"]

    takeover = client.post(
        f"/api/v1/realtime-speech/sessions/{challenger_session['sessionId']}/desktop-binding",
        json={"userId": "live-device-challenger", "manualCode": "318765"},
    )
    assert takeover.status_code == 409
    assert takeover.json()["error"]["details"]["errorCode"] == "desktop_device_live_in_use"

    still_pinned = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/pinned-live-device/active-connection",
        params={
            "manualCode": "318765",
            "pinnedSessionId": owner_session["sessionId"],
            "pinnedBindingId": owner_binding["bindingId"],
        },
    ))
    assert still_pinned["bindingLockState"] == "held"
    assert still_pinned["binding"]["sessionId"] == owner_session["sessionId"]

    unwrap(client.post(
        f"/api/v1/sessions/{owner_session['sessionId']}/end",
        json={"userId": "live-device-owner"},
    ))
    replacement = unwrap(client.post(
        f"/api/v1/realtime-speech/sessions/{challenger_session['sessionId']}/desktop-binding",
        json={"userId": "live-device-challenger", "manualCode": "318765"},
    ))
    assert replacement["sessionId"] == challenger_session["sessionId"]

    released = unwrap(client.get(
        "/api/v1/realtime-speech/desktop-devices/pinned-live-device/active-connection",
        params={
            "manualCode": "318765",
            "pinnedSessionId": owner_session["sessionId"],
            "pinnedBindingId": owner_binding["bindingId"],
        },
    ))
    assert released["bindingLockState"] == "released"
    assert released["binding"]["sessionId"] == challenger_session["sessionId"]


def test_realtime_runtime_tracks_frame_receipts_and_asr_status(monkeypatch) -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "runtime-status-user",
        "title": "伴随助手运行状态测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-runtime-mac",
        "manualCode": "765432",
        "displayName": "面试稳伴随程序 · Runtime Mac",
        "capabilities": {"microphone": "granted", "systemAudio": "prompt", "screenCapture": False},
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "runtime-status-user",
        "manualCode": "765432",
    }))
    bound_runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "runtime-status-user"}))
    assert bound_runtime["stage"] == "bound"
    assert bound_runtime["sessionLive"] is False
    assert bound_runtime["frameReceipts"] == []

    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "runtime-status-user"}))
    live_runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "runtime-status-user"}))
    assert live_runtime["stage"] == "live"
    assert live_runtime["sessionLive"] is True

    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "runtime-status-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "desktop-runtime-mic",
    }))
    speech_service = realtime_speech_service()
    original_save_transcript = speech_service.repository.save_transcript
    transcript_write_count = 0

    def counted_save_transcript(segment):
        nonlocal transcript_write_count
        transcript_write_count += 1
        return original_save_transcript(segment)

    monkeypatch.setattr(speech_service.repository, "save_transcript", counted_save_transcript)
    payload = base64.b64encode("我正在测试麦克风".encode("utf-8")).decode("utf-8")
    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={publisher['token']}") as websocket:
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-runtime-mac",
            "sourceId": "mic-default",
            "sequence": 1,
            "sourceKind": "microphone",
            "segmentId": "seg-runtime-mic",
            "revision": 1,
            "capturedAtMs": 1000,
            "sentAtMs": 1080,
            "traceId": "trace-runtime-mic-1",
            "startedAtMs": 1000,
            "endedAtMs": 1800,
            "lastMeaningfulSpeechAtMs": 1500,
            "durationMs": 800,
            "codec": "pcm-s16le",
            "sampleRateHz": 16000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": payload,
        })
        event = websocket.receive_json()
    assert event["kind"] == "transcript-updated"
    assert transcript_write_count == 1
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "runtime-status-user"}))
    assert runtime["stage"] in {"publishing", "transcribing", "web-visible"}
    assert runtime["frameReceipts"][0]["sourceKind"] == "microphone"
    assert runtime["frameReceipts"][0]["frameCount"] == 1
    assert runtime["frameReceipts"][0]["lastAsrStatus"] == "accepted"
    assert runtime["transcriptCount"] == 1
    assert runtime["performance"]["countersBySource"]["microphone"]["chunksUploaded"] >= 1
    assert "captureToIngestMs" in runtime["performance"]["latestBySource"]["microphone"]
    assert runtime["performance"]["latestBySource"]["microphone"]["traceId"] == "trace-runtime-mic-1"
    assert runtime["performance"]["latestBySource"]["microphone"]["captureToSendMs"] == 80
    assert (
        runtime["performance"]["latestBySource"]["microphone"]["lastMeaningfulSpeechToPublishMs"]
        - runtime["performance"]["latestBySource"]["microphone"]["stopToTerminalMs"]
    ) == 300
    if runtime["sourceHealth"]:
        assert "providerMode" in runtime["sourceHealth"][0]
    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "runtime-status-user"}))
    assert transcripts["transcripts"][0]["publishedAtMs"] is not None
    assert transcripts["transcripts"][0]["performance"]["backendPushMs"] is not None
    assert transcripts["transcripts"][0]["performance"]["traceId"] == "trace-runtime-mic-1"


def test_capture_pause_is_authoritative_and_blocks_audio_until_explicit_resume() -> None:
    user_id = "capture-pause-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "暂停收音测试"}))
    session_id = session["sessionId"]
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "capture-pause-device",
        "manualCode": "764321",
        "displayName": "暂停收音测试 Mac",
        "capabilities": {"microphone": True, "systemAudio": True},
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": user_id,
        "manualCode": "764321",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "pause-test-publisher",
    }))

    paused = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/capture-control", json={
        "userId": user_id,
        "action": "pause",
    }))
    assert paused["captureState"] == "paused"
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": user_id}))
    assert runtime["captureState"] == "paused"
    assert runtime["stage"] == "paused"
    assert runtime["anomalyReasons"] == []
    pairing = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "764321",
        "deviceId": "capture-pause-device",
    }))
    assert pairing["captureState"] == "paused"

    payload = base64.b64encode(b"synthetic paused pcm").decode("utf-8")
    events = realtime_speech_service().process_audio_frame(
        token=publisher["token"], device_id="capture-pause-device", source_id="mic-default",
        sequence=1, source_kind="microphone", segment_id="paused-segment", revision=1,
        captured_at_ms=1000, started_at_ms=1000, ended_at_ms=1200, duration_ms=200,
        codec="pcm-s16le", sample_rate_hz=16000, channels=1, is_final=True,
        trace_id="paused-trace", sent_at_ms=1050, audio_base64=payload,
    )
    assert events == []
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": user_id}))
    assert runtime["frameReceipts"] == []
    assert runtime["transcriptCount"] == 0

    resumed = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/capture-control", json={
        "userId": user_id,
        "action": "resume",
    }))
    assert resumed["captureState"] == "capturing"
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": user_id}))
    assert runtime["captureState"] == "capturing"


def test_same_interview_allows_multiple_observers_without_enabling_multiple_sessions() -> None:
    user_id = "single-active-page-user"
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "单活页面租约测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "single-active-page-device",
        "manualCode": "319901",
        "displayName": "单活页面测试 Mac",
        "capabilities": {"microphone": True, "systemAudio": True},
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": user_id,
        "manualCode": "319901",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

    first = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": user_id,
        "page": "live",
        "pageInstanceId": "page-instance-first",
    }))
    renewed = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": user_id,
        "page": "live",
        "pageInstanceId": "page-instance-first",
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": user_id,
        "page": "preparation",
    }))
    second = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": user_id,
        "page": "live",
        "pageInstanceId": "page-instance-second",
    }))

    assert first["leaseGeneration"] == 1
    assert renewed["leaseGeneration"] == 1
    assert second["leaseGeneration"] == 2
    assert second["pageInstanceId"] == "page-instance-second"
    from app.deps import realtime_speech_service as realtime_speech_service_dep
    realtime_speech_service_dep().require_active_realtime_session(
        user_id=user_id,
        session_id=session_id,
        page_instance_id="page-instance-first",
        lease_generation=first["leaseGeneration"],
    )


def test_realtime_publisher_replacement_keeps_one_authoritative_channel() -> None:
    user_id = "publisher-replacement-user"
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "发布通道替换测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

    first = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "首次连接",
    }))
    second = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "重连后的客户端名称",
    }))

    assert first["publisherId"] != second["publisherId"]
    runtime = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/runtime",
        params={"userId": user_id},
    ))
    assert [item["publisherId"] for item in runtime["publishers"]] == [second["publisherId"]]
    assert runtime["publishers"][0]["status"] == "connected"


def test_realtime_publisher_replacement_preserves_other_logical_channels() -> None:
    user_id = "publisher-channel-isolation-user"
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "发布声道隔离测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

    system = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "system",
        "clientName": "系统输出",
    }))
    mixed = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "双通道传输",
    }))

    runtime = unwrap(client.get(
        f"/api/v1/realtime-speech/sessions/{session_id}/runtime",
        params={"userId": user_id},
    ))
    assert {item["publisherId"] for item in runtime["publishers"]} == {
        system["publisherId"],
        mixed["publisherId"],
    }


def test_live_start_bounds_provider_prewarm_wait(monkeypatch) -> None:
    service = realtime_speech_service()
    user_id = "bounded-prewarm-user"
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "Bounded prewarm",
    }))
    release = threading.Event()
    original_wait = service.settings.realtime_asr_prewarm_wait_seconds
    original_enabled = service.settings.realtime_asr_prewarm_enabled
    original_warm = service.asr_gateway.warm_session
    service.settings.realtime_asr_prewarm_enabled = True
    service.settings.realtime_asr_prewarm_wait_seconds = 0.5
    monkeypatch.setattr(service.asr_gateway, "warm_session", lambda **_kwargs: release.wait(timeout=1))
    try:
        started = monotonic()
        response = client.post(f"/api/v1/sessions/{session['sessionId']}/start", json={"userId": user_id})
        elapsed = monotonic() - started
        assert response.status_code == 200
        # The provider stub blocks for one second and the legacy path waited up
        # to the configured 500 ms. Entry now only schedules the background work.
        assert elapsed < 0.35
    finally:
        release.set()
        service.settings.realtime_asr_prewarm_wait_seconds = original_wait
        service.settings.realtime_asr_prewarm_enabled = original_enabled
        monkeypatch.setattr(service.asr_gateway, "warm_session", original_warm)


def test_preparing_binding_prewarms_both_channels_without_live_publication(monkeypatch) -> None:
    service = realtime_speech_service()
    user_id = "preparing-warm-readiness-user"
    calls: list[str] = []
    ready = threading.Event()
    original_enabled = service.settings.realtime_asr_prewarm_enabled
    original_warm = service.asr_gateway.warm_session
    service.settings.realtime_asr_prewarm_enabled = True

    def record_warm(**kwargs) -> None:
        calls.append(kwargs["source_kind"])
        if {"microphone", "system"}.issubset(calls):
            ready.set()

    monkeypatch.setattr(service.asr_gateway, "warm_session", record_warm)
    try:
        session = unwrap(client.post("/api/v1/sessions", json={
            "userId": user_id,
            "title": "Preparing warm readiness",
        }))
        session_id = session["sessionId"]
        unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
            "deviceId": "device-preparing-warm",
            "manualCode": "674125",
            "displayName": "Preparing warm companion",
            "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": False},
        }))

        unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
            "userId": user_id,
            "manualCode": "674125",
        }))

        assert ready.wait(timeout=1)
        assert set(calls) == {"microphone", "system"}
        assert unwrap(client.get(f"/api/v1/sessions/{session_id}", params={"userId": user_id}))["status"] == "preparing"
        publisher = client.post("/api/v1/realtime-speech/publishers", json={
            "userId": user_id,
            "sessionId": session_id,
            "sourceKind": "mixed",
            "clientName": "must-stay-live-only",
        })
        assert publisher.status_code == 400
        runtime = unwrap(client.get(
            f"/api/v1/realtime-speech/sessions/{session_id}/runtime",
            params={"userId": user_id},
        ))
        assert runtime["publishers"] == []
        assert runtime["frameReceipts"] == []
        assert runtime["transcriptCount"] == 0

        with service._prewarm_metrics_lock:
            service._prewarm_ready_at_by_session[session_id] = {"microphone": 0, "system": 0}
        calls.clear()
        ready.clear()
        unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
            "userId": user_id,
            "manualCode": "674125",
        }))
        assert ready.wait(timeout=1)
        assert set(calls) == {"microphone", "system"}

        service._reset_realtime_session(session_id=session_id, retired=True)
        assert session_id not in service._prewarm_ready_by_session
        assert session_id not in service._prewarm_ready_at_by_session
    finally:
        service.settings.realtime_asr_prewarm_enabled = original_enabled
        monkeypatch.setattr(service.asr_gateway, "warm_session", original_warm)


def test_realtime_runtime_reports_desktop_no_audio_frames_anomaly() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "runtime-anomaly-user",
        "title": "无音频异常测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-runtime-anomaly",
        "manualCode": "112233",
        "displayName": "面试稳伴随程序 · Anomaly",
        "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": False},
    }))
    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "runtime-anomaly-user",
        "manualCode": "112233",
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "runtime-anomaly-user",
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "runtime-anomaly-user"}))
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "runtime-anomaly-user"}))
    assert runtime["dominantBottleneck"] == "desktop_no_audio_frames"
    assert "desktop_no_audio_frames" in runtime["anomalyReasons"]


def test_realtime_speech_suppresses_repetitive_hallucinated_transcript() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "repetitive-user",
        "title": "重复转写抑制测试",
    }))
    session_id = session["sessionId"]
    binding = unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-repeat-1",
        "manualCode": "445522",
        "displayName": "面试稳伴随程序 · Repeat",
        "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": False},
    }))
    bound = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "repetitive-user",
        "manualCode": binding["manualCode"],
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "repetitive-user",
        "bindingId": bound["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "repetitive-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "repetitive-user",
        "sessionId": session_id,
        "sourceKind": "system",
        "clientName": "desktop-system-loopback",
    }))

    repetitive_text = "哪儿让你后续的签约问题？" * 12
    payload = base64.b64encode(repetitive_text.encode("utf-8")).decode("utf-8")
    ingest = unwrap(client.post("/api/v1/realtime-speech/frames", json={
        "type": "audio-frame",
        "token": publisher["token"],
        "deviceId": binding["deviceId"],
        "sourceId": "system-loopback",
        "sequence": 1,
        "sourceKind": "system",
        "segmentId": "seg-repeat-1",
        "revision": 1,
        "capturedAtMs": 1000,
        "startedAtMs": 1000,
        "endedAtMs": 2600,
        "durationMs": 1600,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": True,
        "traceId": "trace-repeat-1",
        "audioBase64": payload,
    }))
    assert ingest == []

    deadline = time() + 2.0
    while time() < deadline:
        runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "repetitive-user"}))
        counters = runtime["performance"]["countersBySource"]["system"]
        if counters["repetitiveResultsSuppressed"] > 0:
            break
        sleep(0.05)
    else:
        raise AssertionError("repetitive suppression counter did not update in time")

    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "repetitive-user"}))
    assert transcripts["transcripts"] == []
    assert runtime["transcriptCount"] == 0
    assert "system:repetitive_transcript_suppressed" in runtime["anomalyReasons"]
    assert runtime["dominantBottleneck"] == "system:repetitive_transcript_suppressed"
    events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "repetitive-user"}))
    assert any(item["kind"] == "degraded" and item["payload"]["reason"] == "repetitive-transcript-suppressed" for item in events["events"])


def test_realtime_speech_suppresses_duplicate_nearby_short_transcript() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "duplicate-user",
        "title": "近邻重复抑制测试",
    }))
    session_id = session["sessionId"]
    registered = unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-duplicate-1",
        "manualCode": "778899",
        "displayName": "面试稳伴随程序 · Duplicate",
        "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": False},
    }))
    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "duplicate-user",
        "manualCode": registered["manualCode"],
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "duplicate-user",
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "duplicate-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "duplicate-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "desktop-duplicate-mic",
    }))

    first_payload = base64.b64encode("你好".encode("utf-8")).decode("utf-8")
    second_payload = base64.b64encode("你好".encode("utf-8")).decode("utf-8")
    for sequence, payload in enumerate((first_payload, second_payload), start=1):
        ingest = unwrap(client.post("/api/v1/realtime-speech/frames", json={
            "type": "audio-frame",
            "token": publisher["token"],
            "deviceId": registered["deviceId"],
            "sourceId": "mic-default",
            "sequence": sequence,
            "sourceKind": "microphone",
            "segmentId": f"seg-duplicate-{sequence}",
            "revision": 1,
            "capturedAtMs": 1000 + (sequence - 1) * 2000,
            "startedAtMs": 1000 + (sequence - 1) * 2000,
            "endedAtMs": 1400 + (sequence - 1) * 2000,
            "durationMs": 400,
            "codec": "pcm-s16le",
            "sampleRateHz": 16000,
            "channels": 1,
            "isFinal": True,
            "traceId": f"trace-duplicate-{sequence}",
            "audioBase64": payload,
        }))
        assert ingest == []

    deadline = time() + 2.0
    while time() < deadline:
        runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "duplicate-user"}))
        counters = runtime["performance"]["countersBySource"]["microphone"]
        if counters["duplicateResultsSuppressed"] > 0:
            break
        sleep(0.05)
    else:
        raise AssertionError("duplicate suppression counter did not update in time")

    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "duplicate-user"}))
    assert len(transcripts["transcripts"]) == 1
    assert transcripts["transcripts"][0]["text"] == "你好"
    assert "microphone:duplicate_transcript_suppressed" in runtime["anomalyReasons"]
    events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "duplicate-user"}))
    assert any(item["kind"] == "degraded" and item["payload"]["reason"] == "duplicate-nearby-transcript-suppressed" for item in events["events"])


def test_realtime_speech_suppresses_interviewer_audio_leaking_into_microphone() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "cross-channel-echo-user",
        "title": "跨声道回声抑制测试",
    }))
    session_id = session["sessionId"]
    registered = unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-cross-channel-echo-1",
        "manualCode": "773311",
        "displayName": "面试稳伴随程序 · Cross Channel Echo",
        "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": False},
    }))
    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "cross-channel-echo-user",
        "manualCode": registered["manualCode"],
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "cross-channel-echo-user",
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "cross-channel-echo-user"}))
    system_publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "cross-channel-echo-user",
        "sessionId": session_id,
        "sourceKind": "system",
        "clientName": "desktop-system-loopback",
    }))
    microphone_publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "cross-channel-echo-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "desktop-default-microphone",
    }))
    transcript_text = "我们先聊一下你最近负责的项目经历"
    payload = base64.b64encode(transcript_text.encode("utf-8")).decode("utf-8")

    unwrap(client.post("/api/v1/realtime-speech/frames", json={
        "type": "audio-frame",
        "token": system_publisher["token"],
        "deviceId": registered["deviceId"],
        "sourceId": "system-loopback",
        "sequence": 1,
        "sourceKind": "system",
        "segmentId": "seg-system-primary",
        "revision": 1,
        "capturedAtMs": 1000,
        "startedAtMs": 1000,
        "endedAtMs": 4000,
        "durationMs": 3000,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": True,
        "traceId": "trace-system-primary",
        "audioBase64": payload,
    }))
    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "cross-channel-echo-user"}))
        if len(transcripts["transcripts"]) == 1:
            break
        sleep(0.05)
    else:
        raise AssertionError("primary system transcript was not published in time")

    unwrap(client.post("/api/v1/realtime-speech/frames", json={
        "type": "audio-frame",
        "token": microphone_publisher["token"],
        "deviceId": registered["deviceId"],
        "sourceId": "default",
        "sequence": 1,
        "sourceKind": "microphone",
        "segmentId": "seg-microphone-echo",
        "revision": 1,
        "capturedAtMs": 1120,
        "startedAtMs": 1120,
        "endedAtMs": 4120,
        "durationMs": 3000,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": True,
        "traceId": "trace-microphone-echo",
        "audioBase64": payload,
    }))
    deadline = time() + 2.0
    while time() < deadline:
        runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "cross-channel-echo-user"}))
        if runtime["performance"]["countersBySource"]["microphone"]["duplicateResultsSuppressed"] > 0:
            break
        sleep(0.05)
    else:
        raise AssertionError("cross-channel microphone echo was not suppressed in time")

    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "cross-channel-echo-user"}))
    assert [(item["sourceKind"], item["role"], item["text"]) for item in transcripts["transcripts"]] == [
        ("system", "interviewer", transcript_text),
    ]
    events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "cross-channel-echo-user"}))
    assert any(item["kind"] == "degraded" and item["payload"]["reason"] == "cross-channel-echo-suppressed" for item in events["events"])


def test_realtime_speech_keeps_late_system_final_authoritative_after_microphone_echo() -> None:
    user_id = "late-system-final-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "系统声道最终结果优先"}))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    system_publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id, "sessionId": session_id, "sourceKind": "system", "clientName": "system-loopback",
    }))
    microphone_publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id, "sessionId": session_id, "sourceKind": "microphone", "clientName": "microphone-echo",
    }))
    question = "你有参加过相关项目吗？"
    payload = base64.b64encode(question.encode("utf-8")).decode("utf-8")

    def publish(*, token: str, source_kind: str, source_id: str, sequence: int, revision: int, is_final: bool) -> None:
        unwrap(client.post("/api/v1/realtime-speech/frames", json={
            "type": "audio-frame", "token": token, "deviceId": "device-late-system-final",
            "sourceId": source_id, "sequence": sequence, "sourceKind": source_kind,
            "segmentId": "seg-system-question" if source_kind == "system" else "seg-microphone-echo",
            "revision": revision, "capturedAtMs": 1_000 + sequence * 100,
            "startedAtMs": 1_000, "endedAtMs": 3_000 + sequence * 100,
            "durationMs": 2_000, "codec": "pcm-s16le", "sampleRateHz": 16_000,
            "channels": 1, "isFinal": is_final, "audioBase64": payload,
        }))

    publish(token=system_publisher["token"], source_kind="system", source_id="system-loopback", sequence=1, revision=1, is_final=False)
    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": user_id}))
        if any(item["sourceKind"] == "system" and not item["isFinal"] for item in transcripts["transcripts"]):
            break
        sleep(0.05)
    else:
        raise AssertionError("system partial was not published")

    publish(token=microphone_publisher["token"], source_kind="microphone", source_id="default", sequence=1, revision=1, is_final=True)
    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": user_id}))
        if any(item["sourceKind"] == "microphone" and item["isFinal"] for item in transcripts["transcripts"]):
            break
        sleep(0.05)
    else:
        raise AssertionError("microphone echo final was not published")

    publish(token=system_publisher["token"], source_kind="system", source_id="system-loopback", sequence=2, revision=2, is_final=True)
    deadline = time() + 3.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": user_id}))
        candidates = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/question-candidates", params={"userId": user_id}))
        if any(item["sourceKind"] == "system" and item["isFinal"] for item in transcripts["transcripts"]) and candidates["candidates"]:
            break
        sleep(0.05)
    else:
        raise AssertionError("late system final did not produce a question candidate")

    assert candidates["candidates"][0]["text"] == question
    assert candidates["candidates"][0]["answerTaskId"] is None
    history = unwrap(client.get(f"/api/v1/live-answer/sessions/{session_id}/history", params={"userId": user_id}))
    assert history == []


def test_realtime_speech_suppressed_final_closes_existing_partial_without_answer() -> None:
    user_id = "suppressed-final-reconcile-user"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "抑制结果收口"}))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id, "sessionId": session_id, "sourceKind": "system", "clientName": "system-loopback",
    }))

    def publish(segment_id: str, sequence: int, revision: int, text: str, is_final: bool, started_at_ms: int) -> None:
        unwrap(client.post("/api/v1/realtime-speech/frames", json={
            "type": "audio-frame", "token": publisher["token"], "deviceId": "device-suppressed-final",
            "sourceId": "system-loopback", "sequence": sequence, "sourceKind": "system",
            "segmentId": segment_id, "revision": revision, "capturedAtMs": started_at_ms,
            "startedAtMs": started_at_ms, "endedAtMs": started_at_ms + 400,
            "durationMs": 400, "codec": "pcm-s16le", "sampleRateHz": 16_000,
            "channels": 1, "isFinal": is_final,
            "audioBase64": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        }))

    publish("seg-greeting-primary", 1, 1, "你好", True, 1_000)
    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": user_id}))
        if any(item["segmentId"] == "seg-greeting-primary" for item in transcripts["transcripts"]):
            break
        sleep(0.05)

    publish("seg-greeting-duplicate", 2, 1, "你", False, 2_000)
    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": user_id}))
        if any(item["segmentId"] == "seg-greeting-duplicate" and not item["isFinal"] for item in transcripts["transcripts"]):
            break
        sleep(0.05)
    else:
        raise AssertionError("duplicate partial was not published")

    publish("seg-greeting-duplicate", 3, 2, "你好", True, 2_000)
    deadline = time() + 2.0
    while time() < deadline:
        transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": user_id}))
        duplicate = next((item for item in transcripts["transcripts"] if item["segmentId"] == "seg-greeting-duplicate"), None)
        if duplicate and duplicate["isFinal"]:
            break
        sleep(0.05)
    else:
        raise AssertionError("suppressed final did not close its partial")

    assert unwrap(client.get(f"/api/v1/live-answer/sessions/{session_id}/history", params={"userId": user_id})) == []
    candidates = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/question-candidates", params={"userId": user_id}))
    assert candidates["candidates"] == []
    events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": user_id}))
    reconciled = [
        item for item in events["events"]
        if item["kind"] == "transcript-updated"
        and item["payload"].get("segmentId") == "seg-greeting-duplicate"
        and item["payload"].get("isFinal") is True
    ]
    assert len(reconciled) == 1
    assert reconciled[0]["payload"]["terminalState"] == "final"


def test_realtime_speech_suppresses_filler_transcript() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "filler-user",
        "title": "口头语抑制测试",
    }))
    session_id = session["sessionId"]
    registered = unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-filler-1",
        "manualCode": "661122",
        "displayName": "面试稳伴随程序 · Filler",
        "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": False},
    }))
    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "filler-user",
        "manualCode": registered["manualCode"],
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": "filler-user",
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "filler-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "filler-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "desktop-filler-mic",
    }))

    payload = base64.b64encode("嗯嗯".encode("utf-8")).decode("utf-8")
    ingest = unwrap(client.post("/api/v1/realtime-speech/frames", json={
        "type": "audio-frame",
        "token": publisher["token"],
        "deviceId": registered["deviceId"],
        "sourceId": "mic-default",
        "sequence": 1,
        "sourceKind": "microphone",
        "segmentId": "seg-filler-1",
        "revision": 1,
        "capturedAtMs": 1000,
        "startedAtMs": 1000,
        "endedAtMs": 1400,
        "durationMs": 400,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": True,
        "traceId": "trace-filler-1",
        "audioBase64": payload,
    }))
    assert ingest == []

    deadline = time() + 2.0
    while time() < deadline:
        runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "filler-user"}))
        counters = runtime["performance"]["countersBySource"]["microphone"]
        if counters["fillerResultsSuppressed"] > 0:
            break
        sleep(0.05)
    else:
        raise AssertionError("filler suppression counter did not update in time")

    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "filler-user"}))
    assert transcripts["transcripts"] == []
    assert "microphone:filler_transcript_suppressed" in runtime["anomalyReasons"]
    events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "filler-user"}))
    assert any(item["kind"] == "degraded" and item["payload"]["reason"] == "filler-transcript-suppressed" for item in events["events"])


def test_realtime_speech_low_confidence_requires_confirmation_and_mixed_source_degrades() -> None:
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "realtime-confirm-user",
        "title": "实时确认测试",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "realtime-confirm-user"}))
    system_publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-confirm-user",
        "sessionId": session_id,
        "sourceKind": "system",
        "clientName": "desktop-system",
    }))
    mixed_publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "realtime-confirm-user",
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "desktop-mixed",
    }))

    low_conf_payload = base64.b64encode("__low_conf__ 讲讲你最有挑战的项目？".encode("utf-8")).decode("utf-8")
    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={system_publisher['token']}") as websocket:
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-realtime-2",
            "sourceId": "system-loopback",
            "sequence": 1,
            "sourceKind": "system",
            "segmentId": "seg-system-low",
            "revision": 1,
            "capturedAtMs": 1000,
            "startedAtMs": 1000,
            "endedAtMs": 2500,
            "durationMs": 1500,
            "codec": "opus",
            "sampleRateHz": 48000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": low_conf_payload,
        })
        websocket.receive_json()
        candidate_event = websocket.receive_json()
    assert candidate_event["kind"] == "question-candidate"

    candidates = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/question-candidates", params={"userId": "realtime-confirm-user"}))
    candidate_id = candidates["candidates"][0]["candidateId"]
    assert candidates["candidates"][0]["state"] == "needs-confirmation"
    confirmed = unwrap(client.post(f"/api/v1/realtime-speech/question-candidates/{candidate_id}/confirm", json={"userId": "realtime-confirm-user"}))
    assert confirmed["state"] == "confirmed"
    assert confirmed["answerTaskId"] is None
    history = unwrap(client.get(f"/api/v1/live-answer/sessions/{session_id}/history", params={"userId": "realtime-confirm-user"}))
    assert history == []

    mixed_payload = base64.b64encode("这是一段混合音频".encode("utf-8")).decode("utf-8")
    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={mixed_publisher['token']}") as websocket:
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-realtime-3",
            "sourceId": "mixed-source",
            "sequence": 1,
            "sourceKind": "mixed",
            "segmentId": "seg-mixed-1",
            "revision": 1,
            "capturedAtMs": 3000,
            "startedAtMs": 3000,
            "endedAtMs": 4000,
            "durationMs": 1000,
            "codec": "opus",
            "sampleRateHz": 48000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": mixed_payload,
        })
        degraded = websocket.receive_json()
    assert degraded["kind"] == "degraded"
    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "realtime-confirm-user"}))
    assert runtime["latestState"] in {"degraded", "closed", "connected", "failed"}
