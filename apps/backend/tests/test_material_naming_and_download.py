from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.deps import document_service
from app.main import create_app
from app.ports.document_repository import DocumentRecord


client = TestClient(create_app())


def unwrap(response):
    payload = response.json()
    assert response.status_code == 200, payload
    return payload["data"]


def upload_resume(*, user_id: str, filename: str, payload: bytes) -> dict:
    intent = unwrap(client.post("/api/v1/resume/upload-intents", json={
        "userId": user_id,
        "filename": filename,
        "contentType": "text/markdown",
        "sizeBytes": len(payload),
    }))
    proxied = client.post(
        "/api/v1/resume/uploads/proxy",
        data={
            "userId": user_id,
            "intentId": intent["intentId"],
            "objectKey": intent["objectKey"],
            "contentType": "text/markdown",
        },
        files={"file": (filename, payload, "text/markdown")},
    )
    assert proxied.status_code == 200, proxied.text
    return unwrap(client.post("/api/v1/resume/uploads/complete", json={
        "userId": user_id,
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": "text/markdown",
        "sizeBytes": len(payload),
        "etag": f"test:{len(payload)}",
    }))


def test_duplicate_upload_names_are_unique_and_original_names_are_preserved() -> None:
    user_id = f"material-name-{uuid4().hex}"
    first = upload_resume(user_id=user_id, filename="面试准备.md", payload=b"# first")
    second = upload_resume(user_id=user_id, filename="面试准备.md", payload=b"# second")

    assert first["source"]["displayName"] == "面试准备.md"
    assert second["source"]["displayName"] == "面试准备 (2).md"
    listed = unwrap(client.get("/api/v1/documents", params={"userId": user_id}))
    assert {item["displayName"] for item in listed} == {"面试准备.md", "面试准备 (2).md"}
    assert {item["originalFilename"] for item in listed} == {"面试准备.md"}


def test_historical_duplicate_names_receive_stable_list_labels() -> None:
    service = document_service()
    user_id = f"historical-name-{uuid4().hex}"
    for index in range(2):
        identifier = f"historical-{uuid4().hex}"
        service.repository.save(DocumentRecord(
            document_id=identifier,
            owner_user_id=user_id,
            document_kind="knowledge",
            display_name="历史资料.md",
            file_kind="md",
            content_type="text/markdown",
            size_bytes=10,
            object_key=f"synthetic/{identifier}.md",
            status="ready",
            knowledge_collection_id=None,
            processing_requested_at_ms=None,
            deleted_at_ms=None,
            created_at_ms=100 + index,
            updated_at_ms=100 + index,
            summary="synthetic",
            original_filename="历史资料.md",
            index_state="indexed",
        ))

    first_listing = service.list_documents(user_id=user_id)
    second_listing = service.list_documents(user_id=user_id)
    assert [item.display_name for item in first_listing] == [item.display_name for item in second_listing]
    assert {item.display_name for item in first_listing} == {"历史资料.md", "历史资料 (2).md"}


def test_material_rename_is_persistent_unique_and_owner_scoped() -> None:
    owner = f"rename-owner-{uuid4().hex}"
    other = f"rename-other-{uuid4().hex}"
    first = upload_resume(user_id=owner, filename="one.md", payload=b"one")
    second = upload_resume(user_id=owner, filename="two.md", payload=b"two")
    first_id = first["source"]["sourceId"]
    second_id = second["source"]["sourceId"]

    renamed = unwrap(client.patch(f"/api/v1/documents/{first_id}/display-name", json={
        "userId": owner,
        "displayName": "我的面试资料.md",
    }))
    assert renamed["displayName"] == "我的面试资料.md"
    collision = unwrap(client.patch(f"/api/v1/documents/{second_id}/display-name", json={
        "userId": owner,
        "displayName": "我的面试资料.md",
    }))
    assert collision["displayName"] == "我的面试资料 (2).md"
    forbidden = client.patch(f"/api/v1/documents/{first_id}/display-name", json={
        "userId": other,
        "displayName": "越权修改.md",
    })
    assert forbidden.status_code == 403
    detail = unwrap(client.get(f"/api/v1/documents/{first_id}", params={"userId": owner}))
    assert detail["displayName"] == "我的面试资料.md"
    assert detail["originalFilename"] == "one.md"


def test_original_file_download_preserves_bytes_headers_and_permissions() -> None:
    owner = f"download-owner-{uuid4().hex}"
    other = f"download-other-{uuid4().hex}"
    original = "# synthetic material\nhello".encode()
    completed = upload_resume(user_id=owner, filename="合成资料.md", payload=original)
    document_id = completed["source"]["sourceId"]

    response = client.get(f"/api/v1/documents/{document_id}/download", params={"userId": owner})
    assert response.status_code == 200
    assert response.content == original
    assert response.headers["content-type"].startswith("text/markdown")
    assert "filename*=UTF-8''" in response.headers["content-disposition"]
    assert "%E5%90%88%E6%88%90%E8%B5%84%E6%96%99.md" in response.headers["content-disposition"]
    assert "objectKey" not in response.text

    forbidden = client.get(f"/api/v1/documents/{document_id}/download", params={"userId": other})
    assert forbidden.status_code == 403
    assert original not in forbidden.content

    assert client.delete(f"/api/v1/documents/{document_id}", params={"userId": owner}).status_code == 200
    deleted = client.get(f"/api/v1/documents/{document_id}/download", params={"userId": owner})
    assert deleted.status_code == 404


def test_missing_original_object_returns_safe_not_found() -> None:
    service = document_service()
    owner = f"missing-download-{uuid4().hex}"
    identifier = f"missing-{uuid4().hex}"
    service.repository.save(DocumentRecord(
        document_id=identifier,
        owner_user_id=owner,
        document_kind="resume",
        display_name="missing.md",
        file_kind="md",
        content_type="text/markdown",
        size_bytes=10,
        object_key=f"synthetic/missing/{identifier}.md",
        status="ready",
        knowledge_collection_id=None,
        processing_requested_at_ms=None,
        deleted_at_ms=None,
        created_at_ms=1,
        updated_at_ms=1,
        summary="synthetic",
        original_filename="missing.md",
        index_state="indexed",
    ))
    response = client.get(f"/api/v1/documents/{identifier}/download", params={"userId": owner})
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "原文件暂时不可下载，请稍后重试。"
    assert identifier not in response.text
