from __future__ import annotations

from time import sleep, time

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def unwrap(response):
    payload = response.json()
    assert response.status_code == 200, payload
    assert "requestId" in payload
    assert "meta" in payload
    return payload["data"]


def test_synthetic_material_upload_index_session_rag_and_delete_exclusion() -> None:
    user_id = "synthetic-material-e2e-user"
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": user_id,
        "name": "合成面试资料库",
    }))
    intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents", json={
        "userId": user_id,
        "filename": "payment-risk-notes.txt",
        "contentType": "text/plain",
        "sizeBytes": 2048,
    }))
    completed = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": user_id,
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/plain",
        "sizeBytes": 2048,
        "etag": "synthetic-etag",
        "contentSha256": "c" * 64,
    }))
    document_id = completed["source"]["sourceId"]

    latest = None
    deadline = time() + 5
    while time() < deadline:
        documents = unwrap(client.get("/api/v1/documents", params={"userId": user_id}))
        latest = next((item for item in documents if item["documentId"] == document_id), None)
        if latest and latest["status"] == "ready" and latest["indexState"] == "indexed":
            break
        sleep(0.1)
    assert latest is not None
    assert latest["documentVersionId"]

    processing = unwrap(client.get(f"/api/v1/document-processing/documents/{document_id}", params={"userId": user_id}))
    assert processing["latestTask"]["currentStage"] == "COMPLETED"
    assert processing["latestTask"]["chunkCount"] >= 1

    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "合成资料 RAG 面试",
    }))
    session_id = session["sessionId"]
    confirmed = unwrap(client.post(f"/api/v1/sessions/{session_id}/materials/confirm", json={
        "userId": user_id,
        "knowledgeDocumentIds": [document_id],
    }))
    bound = confirmed["materialBinding"]["boundDocuments"][0]
    assert bound["documentVersionId"] == latest["documentVersionId"]
    assert bound["indexState"] == "indexed"
    assert bound["active"] is True

    started = unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    assert started["status"] == "live"

    answer = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": user_id,
        "sessionId": session_id,
        "question": "请介绍一下这个支付风控相关项目经验",
        "stream": False,
    }))
    retrieval = answer["retrieval"]
    assert retrieval["finalCount"] >= 1
    assert retrieval["chunks"][0]["documentId"] == document_id
    assert retrieval["chunks"][0]["metadata"]["documentVersionId"] == latest["documentVersionId"]

    deleted = unwrap(client.request("DELETE", f"/api/v1/documents/{document_id}", params={"userId": user_id}, json={"userId": user_id}))
    assert deleted["status"] == "deleted"

    post_delete_answer = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": user_id,
        "sessionId": session_id,
        "question": "删除后还能引用这份资料吗",
        "stream": False,
    }))
    assert post_delete_answer["retrieval"]["finalCount"] == 0
