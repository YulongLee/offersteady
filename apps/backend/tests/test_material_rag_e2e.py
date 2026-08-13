from __future__ import annotations

from time import sleep, time

from fastapi.testclient import TestClient

from app.main import create_app
from app.deps import billing_service


client = TestClient(create_app())


def unwrap(response):
    payload = response.json()
    assert response.status_code == 200, payload
    assert "requestId" in payload
    assert "meta" in payload
    return payload["data"]


def test_synthetic_material_upload_index_session_rag_and_delete_exclusion() -> None:
    user_id = "synthetic-material-e2e-user"
    balance_before = billing_service().state_for_user(user_id=user_id).balance
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
        "confirmIndexCharge": True,
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
    billing_after_index = billing_service().state_for_user(user_id=user_id)
    assert billing_after_index.balance == balance_before - 20
    index_entries = [item for item in billing_after_index.ledger if item.kind == "knowledge_index_settlement"]
    assert len(index_entries) == 1
    assert index_entries[0].points == -20

    repeated = unwrap(client.post(f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete", json={
        "userId": user_id,
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/plain",
        "sizeBytes": 2048,
        "etag": "synthetic-etag",
        "contentSha256": "c" * 64,
        "confirmIndexCharge": True,
    }))
    assert repeated["documentVersionId"] == completed["documentVersionId"]
    billing_after_replay = billing_service().state_for_user(user_id=user_id)
    assert billing_after_replay.balance == balance_before - 20
    assert len([item for item in billing_after_replay.ledger if item.kind == "knowledge_index_settlement"]) == 1

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


def test_knowledge_collection_rename_delete_and_owner_isolation() -> None:
    stamp = str(int(time() * 1000))
    owner_auth = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": f"synthetic-collection-owner-{stamp}",
        "password": "SyntheticCollection123@",
        "displayName": "Synthetic owner",
        "clientLabel": "collection-lifecycle-test",
    }))
    other_auth = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": f"synthetic-collection-other-{stamp}",
        "password": "SyntheticCollection123@",
        "displayName": "Synthetic other",
        "clientLabel": "collection-lifecycle-test",
    }))
    owner = owner_auth["user"]["userId"]
    other = other_auth["user"]["userId"]
    owner_headers = {"Authorization": f"Bearer {owner_auth['tokens']['accessToken']}"}
    other_headers = {"Authorization": f"Bearer {other_auth['tokens']['accessToken']}"}
    collection = unwrap(client.post("/api/v1/knowledge/collections", json={
        "userId": owner,
        "name": "旧资料库名称",
    }, headers=owner_headers))
    collection_id = collection["collectionId"]

    renamed = unwrap(client.patch(f"/api/v1/knowledge/collections/{collection_id}", json={
        "userId": owner,
        "name": "新资料库名称",
    }, headers=owner_headers))
    assert renamed["name"] == "新资料库名称"

    owner_state = unwrap(client.get("/api/v1/web/state", headers=owner_headers))
    assert any(item["id"] == collection_id and item["name"] == "新资料库名称" for item in owner_state["knowledgeCollections"])

    intent = unwrap(client.post(f"/api/v1/knowledge/collections/{collection_id}/upload-intents", json={
        "userId": owner,
        "filename": "collection-delete-regression.txt",
        "contentType": "text/plain",
        "sizeBytes": 128,
    }, headers=owner_headers))
    completed = unwrap(client.post(f"/api/v1/knowledge/collections/{collection_id}/uploads/complete", json={
        "userId": owner,
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/plain",
        "sizeBytes": 128,
        "etag": "synthetic-collection-delete-etag",
        "contentSha256": "d" * 64,
        "confirmIndexCharge": True,
    }, headers=owner_headers))
    document_id = completed["source"]["sourceId"]

    forbidden_rename = client.patch(f"/api/v1/knowledge/collections/{collection_id}", json={
        "userId": other,
        "name": "越权重命名",
    }, headers=other_headers)
    assert forbidden_rename.status_code == 403
    forbidden_delete = client.delete(f"/api/v1/knowledge/collections/{collection_id}", params={"userId": other}, headers=other_headers)
    assert forbidden_delete.status_code == 403

    deleted = unwrap(client.delete(f"/api/v1/knowledge/collections/{collection_id}", params={"userId": owner}, headers=owner_headers))
    assert deleted["collectionId"] == collection_id
    state_after_delete = unwrap(client.get("/api/v1/web/state", headers=owner_headers))
    assert all(item["id"] != collection_id for item in state_after_delete["knowledgeCollections"])
    deleted_documents = unwrap(client.get("/api/v1/documents", params={"userId": owner, "includeDeleted": True}, headers=owner_headers))
    assert next(item for item in deleted_documents if item["documentId"] == document_id)["status"] == "deleted"

    missing = client.delete(f"/api/v1/knowledge/collections/{collection_id}", params={"userId": owner}, headers=owner_headers)
    assert missing.status_code == 404
