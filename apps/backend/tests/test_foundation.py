from __future__ import annotations

import base64
import logging
from pathlib import Path
from time import sleep, time

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.ports.authentication import SmsChallengeRecord
from app.ports.realtime_speech import AudioFrame, RealtimeEvent
from app.ports.chat import PromptBuildResult, PromptConfig
from app.services.chat_service import NonRetryableChatError, QwenCompatibleGateway, RetryableChatError
from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.sms_verification_provider import AliyunDypnsSmsVerificationProvider


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
    assert processing["latestTask"]["chunkCount"] >= 1


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
    })
    assert response.status_code == 403


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
    assert any(event["eventName"] == "embedding_chunking_started" for event in retried_status["events"])
    assert any(event["eventName"] == "embedding_started" for event in retried_status["events"])
    assert any(event["eventName"] == "vector_writing_started" for event in retried_status["events"])
    assert retried_status["latestTask"]["parserProvider"] in {"text-parser", "inline-text", "mineru"}


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


def test_knowledge_retrieval_prevents_cross_user_leakage() -> None:
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
    assert payload["finalCount"] >= 1
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
    assert answer["task"]["promptVersion"] == "v3"
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
    gateway = QwenCompatibleGateway(settings)

    cases = [
        (FakeResponse(401), NonRetryableChatError, "chat_provider_auth_failed"),
        (FakeResponse(403), NonRetryableChatError, "chat_provider_auth_failed"),
        (FakeResponse(429), RetryableChatError, "chat_provider_rate_limited"),
        (FakeResponse(503), RetryableChatError, "chat_provider_unavailable"),
        (httpx.ConnectError("offline"), RetryableChatError, "chat_provider_unavailable"),
    ]
    for response, error_type, code in cases:
        monkeypatch.setattr("app.services.chat_service.httpx.Client", lambda *_args, response=response, **_kwargs: FakeClient(response))
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
    assert [event["chunk"]["sequence"] for event in chunk_events] == list(range(1, len(chunk_events) + 1))
    assert events[-1]["type"] == "completed"
    assert events[-1]["task"]["status"] == "completed"
    assert events[-1]["task"]["answerText"]
    persisted = unwrap(client.get(f"/api/v1/live-answer/tasks/{events[-1]['task']['taskId']}", params={"userId": "chat-stream-user"}))
    assert persisted["status"] == "completed"
    assert persisted["answerText"] == events[-1]["task"]["answerText"]


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
    assert events[-1]["partialText"] == "这是已经生成的部分回答。"


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
    assert len(state["interviews"]) == 5
    assert state["interviews"][0]["title"] == "最近面试 6"
    assert all(item["title"] != "最近面试 1" for item in state["interviews"])


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

    failed = unwrap(client.post("/api/v1/screenshot-answer/tasks", json={
        "userId": "screenshot-retry-user",
        "sessionId": session_id,
        "imageIds": [upload["imageId"]],
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

    history = unwrap(client.get(f"/api/v1/screenshot-answer/sessions/{session_id}/history", params={
        "userId": "remote-screenshot-user",
    }))
    assert any(item["taskId"] == loaded["answerTask"]["taskId"] for item in history)


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


def test_realtime_speech_websocket_generates_transcript_question_and_answer() -> None:
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

    question_text = "请介绍一下你最近做的项目？"
    payload = base64.b64encode(question_text.encode("utf-8")).decode("utf-8")
    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={publisher['token']}") as websocket:
        websocket.send_json({
            "type": "audio-frame",
            "deviceId": "device-realtime-1",
            "sourceId": "system-loopback",
            "sequence": 1,
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
        third = websocket.receive_json()

    assert first["kind"] == "transcript-updated"
    assert first["payload"]["role"] == "interviewer"
    assert second["kind"] == "question-confirmed"
    assert second["payload"]["text"] == question_text
    assert third["kind"] == "answer-completed"
    assert third["payload"]["status"] == "completed"

    runtime = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "realtime-user"}))
    assert runtime["transcriptCount"] == 1
    assert runtime["questionCandidateCount"] == 1
    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "realtime-user"}))
    assert transcripts["transcripts"][0]["text"] == question_text
    candidates = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/question-candidates", params={"userId": "realtime-user"}))
    assert candidates["candidates"][0]["state"] == "confirmed"
    history = unwrap(client.get(f"/api/v1/live-answer/sessions/{session_id}/history", params={"userId": "realtime-user"}))
    assert history[0]["question"] == question_text
    context = unwrap(client.get(f"/api/v1/sessions/{session_id}/context", params={"userId": "realtime-user"}))
    assert any(item["role"] == "interviewer" and item["content"] == question_text for item in context["entries"])
    assert any(item["role"] == "assistant" for item in context["entries"])
    usage = unwrap(client.get(f"/api/v1/sessions/{session_id}/usage", params={"userId": "realtime-user"}))
    assert any(item["providerName"] == "qwen-realtime-asr-compatible" for item in usage["records"])
    events = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/events", params={"userId": "realtime-user"}))
    assert any(item["kind"] == "answer-completed" for item in events["events"])


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
            "sequence": 1,
            "sourceKind": "microphone",
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
        assert accepted["payload"]["sequence"] == 1
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
    )

    first = gateway.transcribe(frame=frame_one, attempt=0)
    second = gateway.transcribe(frame=frame_two, attempt=0)

    assert first.text == "第一段 final"
    assert second.text == "第二段 final"
    assert len(fake_connections) == 1
    assert gateway.diagnostics("microphone")["connection_recreations"] == 1
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

    binding = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": "desktop-binding-user",
        "manualCode": "654321",
    }))
    assert binding["deviceId"] == "device-stable-mac"
    assert binding["manualCode"] == "654321"
    assert binding["capabilities"]["screenCapture"] is True

    loaded = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", params={"userId": "desktop-binding-user"}))
    assert loaded["bindingId"] == binding["bindingId"]

    stale_status = unwrap(client.get("/api/v1/realtime-speech/desktop-devices/pairing-status", params={
        "manualCode": "654321",
        "deviceId": "device-stable-mac",
    }))
    assert stale_status["state"] == "stale-bound"
    assert stale_status["bound"] is False
    assert stale_status["staleReason"] == "web-heartbeat-missing"

    stale_active = client.get("/api/v1/realtime-speech/desktop-devices/device-stable-mac/binding", params={"manualCode": "654321"})
    assert stale_active.status_code == 404

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

    status = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/device-status", json={
        "userId": "desktop-binding-user",
        "deviceId": "device-new-generation",
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


def test_realtime_runtime_tracks_frame_receipts_and_asr_status() -> None:
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
            "durationMs": 800,
            "codec": "pcm-s16le",
            "sampleRateHz": 16000,
            "channels": 1,
            "isFinal": True,
            "audioBase64": payload,
        })
        event = websocket.receive_json()
    assert event["kind"] == "transcript-updated"
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
    if runtime["sourceHealth"]:
        assert "providerMode" in runtime["sourceHealth"][0]
    transcripts = unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "runtime-status-user"}))
    assert transcripts["transcripts"][0]["publishedAtMs"] is not None
    assert transcripts["transcripts"][0]["performance"]["backendPushMs"] is not None
    assert transcripts["transcripts"][0]["performance"]["traceId"] == "trace-runtime-mic-1"


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
    assert confirmed["answerTaskId"]

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
