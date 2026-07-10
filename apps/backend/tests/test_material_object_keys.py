from __future__ import annotations

from app.core.config import Settings
from app.services.material_object_keys import MaterialObjectKeyFactory


def test_material_original_key_is_environment_scoped_and_privacy_safe() -> None:
    factory = MaterialObjectKeyFactory(Settings(
        app_name="test",
        environment="test",
        oss_key_prefix="materials",
        oss_environment_label="local-dev",
        material_user_hash_salt="unit-test-salt",
    ))

    key = factory.original_key(
        owner_user_id="prototype-user@example.com",
        document_kind="resume",
        document_id="document-1",
        document_version_id="version-1",
        object_id="object-1",
        file_kind="pdf",
    )

    assert key.startswith("materials/local-dev/users/")
    assert key.endswith("/documents/resume/document-1/versions/version-1/original/object-1.pdf")
    assert "prototype-user" not in key
    assert "example.com" not in key


def test_material_processed_temporary_deletion_and_export_keys_are_classified() -> None:
    factory = MaterialObjectKeyFactory(Settings(app_name="test", environment="test", material_user_hash_salt="unit-test-salt"))

    normalized = factory.processed_artifact_key(
        owner_user_id="user-1",
        document_kind="knowledge",
        document_id="document-1",
        document_version_id="version-1",
        artifact_kind="normalized_markdown",
    )
    chunks = factory.processed_artifact_key(
        owner_user_id="user-1",
        document_kind="knowledge",
        document_id="document-1",
        document_version_id="version-1",
        artifact_kind="chunk_manifest",
    )
    marker = factory.deletion_marker_key(
        owner_user_id="user-1",
        document_kind="knowledge",
        document_id="document-1",
        document_version_id="version-1",
        deleted_at_ms=123456,
    )
    temporary = factory.temporary_upload_key(owner_user_id="user-1", upload_intent_id="intent-1", object_id="object-1", file_kind="docx")
    exported = factory.export_key(owner_user_id="user-1", export_id="export-1", object_id="object-1", extension=".json")

    assert normalized.endswith("/processed/normalized.md")
    assert chunks.endswith("/processed/chunks.jsonl")
    assert marker.endswith("/deleted/123456.json")
    assert temporary.endswith("/tmp/intent-1/object-1.docx")
    assert exported.endswith("/exports/export-1/object-1.json")


def test_material_object_ids_are_path_safe() -> None:
    factory = MaterialObjectKeyFactory(Settings(app_name="test", environment="test", material_object_id_bytes=16))

    object_id = factory.new_object_id()

    assert len(object_id) == 32
    assert "/" not in object_id
