from __future__ import annotations

from fastapi.testclient import TestClient

from app.deps import document_processing_service, storage_port
from app.main import create_app
from app.ports.document_repository import DocumentRecord
from app.ports.document_processing import ProcessingTaskRecord
from app.services.knowledge_index_quote import estimate_normalized_markdown_tokens


client = TestClient(create_app())


def _unwrap(response):
    payload = response.json()
    assert response.status_code == 200, payload
    return payload["data"]


def _prepare_quote(*, user_id: str, collection_id: str, filename: str, content_type: str, payload: bytes):
    intent = _unwrap(client.post(
        f"/api/v1/knowledge/collections/{collection_id}/upload-intents",
        json={
            "userId": user_id,
            "filename": filename,
            "contentType": content_type,
            "sizeBytes": len(payload),
        },
    ))
    uploaded = _unwrap(client.post(
        f"/api/v1/knowledge/collections/{collection_id}/uploads/proxy",
        data={
            "userId": user_id,
            "intentId": intent["intentId"],
            "objectKey": intent["objectKey"],
            "contentType": content_type,
        },
        files={"file": (filename, payload, content_type)},
    ))
    request = {
        "userId": user_id,
        "intentId": intent["intentId"],
        "objectKey": intent["objectKey"],
        "contentType": content_type,
        "sizeBytes": int(uploaded["sizeBytes"]),
        "etag": str(uploaded["etag"]),
    }
    quote = _unwrap(client.post(
        f"/api/v1/knowledge/collections/{collection_id}/uploads/quote",
        json=request,
    ))
    return intent, request, quote


def test_estimator_counts_normalized_content_not_container_bytes() -> None:
    markdown = "# 支付系统\n\n幂等、对账与补偿。\n"
    assert estimate_normalized_markdown_tokens(markdown) == estimate_normalized_markdown_tokens(markdown)
    assert estimate_normalized_markdown_tokens(markdown) < len(b"%PDF" + b"binary-assets" * 100_000) // 4
    assert estimate_normalized_markdown_tokens("   ") == 0


def test_pdf_quote_ignores_large_binary_container_and_confirm_binds_quote() -> None:
    user_id = "content-quote-pdf-user"
    collection = _unwrap(client.post("/api/v1/knowledge/collections", json={"userId": user_id, "name": "PDF 报价"}))
    payload = b"%PDF-1.7\n" + b"synthetic-binary-font-and-image-stream" * 40_000
    _intent, request, quote = _prepare_quote(
        user_id=user_id,
        collection_id=collection["collectionId"],
        filename="synthetic.pdf",
        content_type="application/pdf",
        payload=payload,
    )

    assert quote["tokenCount"] < len(payload) // 100
    assert quote["pointCost"] == 20
    assert quote["documentVersionId"]
    assert storage_port().object_exists(object_key=request["objectKey"])

    completed = _unwrap(client.post(
        f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete",
        json={**request, "confirmIndexCharge": True, "quoteId": quote["quoteId"]},
    ))
    assert completed["documentVersionId"] == quote["documentVersionId"]


def test_quote_from_another_document_version_is_rejected() -> None:
    user_id = "content-quote-binding-user"
    collection = _unwrap(client.post("/api/v1/knowledge/collections", json={"userId": user_id, "name": "报价绑定"}))
    _first_intent, _first_request, first_quote = _prepare_quote(
        user_id=user_id,
        collection_id=collection["collectionId"],
        filename="first.md",
        content_type="text/markdown",
        payload=b"# first\n\nsynthetic content",
    )
    _second_intent, second_request, _second_quote = _prepare_quote(
        user_id=user_id,
        collection_id=collection["collectionId"],
        filename="second.md",
        content_type="text/markdown",
        payload=b"# second\n\nother synthetic content",
    )

    response = client.post(
        f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/complete",
        json={**second_request, "confirmIndexCharge": True, "quoteId": first_quote["quoteId"]},
    )
    assert response.status_code == 409
    assert "当前文件不匹配" in response.json()["error"]["message"]


def test_empty_text_does_not_create_a_quote() -> None:
    user_id = "content-quote-empty-user"
    collection = _unwrap(client.post("/api/v1/knowledge/collections", json={"userId": user_id, "name": "空内容"}))
    intent = _unwrap(client.post(
        f"/api/v1/knowledge/collections/{collection['collectionId']}/upload-intents",
        json={"userId": user_id, "filename": "empty.md", "contentType": "text/markdown", "sizeBytes": 3},
    ))
    uploaded = _unwrap(client.post(
        f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/proxy",
        data={"userId": user_id, "intentId": intent["intentId"], "objectKey": intent["objectKey"], "contentType": "text/markdown"},
        files={"file": ("empty.md", b"   ", "text/markdown")},
    ))
    response = client.post(
        f"/api/v1/knowledge/collections/{collection['collectionId']}/uploads/quote",
        json={
            "userId": user_id,
            "intentId": intent["intentId"],
            "objectKey": intent["objectKey"],
            "contentType": "text/markdown",
            "sizeBytes": uploaded["sizeBytes"],
            "etag": uploaded["etag"],
        },
    )
    assert response.status_code == 422
    assert "不会扣除积分" in response.json()["error"]["message"]


def test_quote_parse_artifact_is_reused(monkeypatch) -> None:
    service = document_processing_service()
    storage = storage_port()
    object_key = "synthetic/content-quote-cache/source.md"
    storage.uploaded_objects[object_key] = b"# cached\n\nonly parse once"
    document = DocumentRecord(
        document_id="document-content-quote-cache",
        owner_user_id="content-quote-cache-user",
        document_kind="knowledge",
        display_name="source.md",
        file_kind="md",
        content_type="text/markdown",
        size_bytes=26,
        object_key=object_key,
        status="uploaded",
        knowledge_collection_id="collection-content-quote-cache",
        processing_requested_at_ms=None,
        deleted_at_ms=None,
        created_at_ms=1,
        updated_at_ms=1,
        summary=None,
        document_version_id="version-content-quote-cache",
    )
    parser = service.parser_service.binary_parser
    original_parse = parser.parse
    calls = 0

    def counting_parse(*, context, payload):
        nonlocal calls
        calls += 1
        return original_parse(context=context, payload=payload)

    monkeypatch.setattr(parser, "parse", counting_parse)
    first = service.parse_document_for_quote(document=document)
    second = service.parse_document_for_quote(document=document)

    assert first == second
    assert calls == 1


def test_retry_uses_cached_text_instead_of_original_file_size() -> None:
    service = document_processing_service()
    storage = storage_port()
    user_id = "content-quote-retry-user"
    object_key = "synthetic/content-quote-retry/large.pdf"
    storage.uploaded_objects[object_key] = b"%PDF" + b"binary" * 500_000
    document = service.document_repository.save(DocumentRecord(
        document_id="document-content-quote-retry",
        owner_user_id=user_id,
        document_kind="knowledge",
        display_name="large.pdf",
        file_kind="pdf",
        content_type="application/pdf",
        size_bytes=len(storage.uploaded_objects[object_key]),
        object_key=object_key,
        status="failed",
        knowledge_collection_id="collection-content-quote-retry",
        processing_requested_at_ms=1,
        deleted_at_ms=None,
        created_at_ms=1,
        updated_at_ms=1,
        summary="synthetic failed document",
        document_version_id="version-content-quote-retry",
    ))
    service.parser_service.save_normalized_artifact(document=document, markdown="# retry\n\nsmall normalized content\n")
    task = service.task_repository.save_task(ProcessingTaskRecord(
        task_id="task-content-quote-retry",
        document_id=document.document_id,
        owner_user_id=user_id,
        document_kind="knowledge",
        current_stage="FAILED",
        retry_count=0,
        max_retries=1,
        parser_provider="synthetic",
        embedding_provider="synthetic",
        created_at_ms=1,
        updated_at_ms=1,
    ))

    retried = service.retry_task(task_id=task.task_id, user_id=user_id)
    assert retried.billing_quote_id is not None
    quote = service.billing_service.knowledge_index_quote(
        user_id=user_id,
        quote_id=retried.billing_quote_id,
        document_version_id=document.document_version_id,
    )
    assert quote.token_estimate < 100
    assert quote.points_required == 20
