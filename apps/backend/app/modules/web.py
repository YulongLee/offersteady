from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import get_settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import (
    authentication_service,
    billing_service,
    chat_service,
    document_read_service,
    document_service,
    optional_authenticated_context,
    screenshot_answer_service,
    session_service,
    storage_port,
)
from app.ports.commercial_hardening import CommercialHardeningRepository
from app.ports.authentication import AuthenticatedRequestContext, UserRecord
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.services.billing_service import BillingService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.screenshot_answer_service import ScreenshotAnswerService
from app.services.session_service import SessionService
from app.ports.storage import FileStoragePort


router = APIRouter(prefix="/web", tags=["web"])
descriptor = ModuleDescriptor(
    feature="web",
    owningApp="apps/backend",
    routePrefix="/api/v1/web",
    mode="active",
    notes="API-only Web application state contract for frontend pages.",
)


def _desktop_release_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "apps" / "desktop" / "release"


def _published_desktop_manifest_path() -> Path:
    return Path(__file__).resolve().parents[1] / "desktop_release_manifest.json"


def _published_desktop_manifest() -> dict[str, object] | None:
    manifest_path = _published_desktop_manifest_path()
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) and isinstance(payload.get("entries"), list) else None


def _published_desktop_entry(filename: str) -> dict[str, object] | None:
    manifest = _published_desktop_manifest()
    if manifest is None:
        return None
    return next((entry for entry in manifest["entries"] if isinstance(entry, dict) and entry.get("fileName") == filename), None)


@router.get("/downloads/desktop/{filename}")
async def download_desktop_artifact(
    filename: str,
    storage: FileStoragePort = Depends(storage_port),
) -> Response:
    if "/" in filename or "\\" in filename or not filename.startswith("OfferSteady-Companion-") or not filename.endswith((".zip", ".dmg")):
        raise HTTPException(status_code=404, detail="Desktop artifact not found")
    release_dir = _desktop_release_dir().resolve()
    artifact = (release_dir / filename).resolve()
    if artifact.is_file() and artifact.is_relative_to(release_dir):
        return FileResponse(
            path=str(artifact),
            filename=artifact.name,
            media_type="application/zip" if artifact.suffix == ".zip" else "application/x-apple-diskimage",
        )
    entry = _published_desktop_entry(filename)
    object_key = entry.get("objectKey") if entry else None
    if not isinstance(object_key, str) or not object_key:
        raise HTTPException(status_code=404, detail="Desktop artifact not found")
    signed_url = storage.create_signed_download_url(
        object_key=object_key,
        expires_seconds=get_settings().desktop_release_download_ttl_seconds,
    )
    if not signed_url:
        raise HTTPException(status_code=503, detail="Desktop artifact storage is unavailable")
    return RedirectResponse(url=signed_url, status_code=307)


def _account_payload(user: UserRecord | None) -> dict[str, object]:
    if user is None:
        return {
            "id": "anonymous",
            "displayName": "访客",
            "createdAtMs": 1_719_000_000_000,
            "bindings": [
                {
                    "id": "anonymous-prototype-binding",
                    "provider": "prototype",
                    "displayName": "未登录访客",
                    "status": "active",
                    "boundAtMs": 1_719_000_000_000,
                    "canUnbind": False,
                }
            ],
        }
    return {
        "id": user.user_id,
        "displayName": user.display_name,
        "createdAtMs": user.created_at_ms,
        "bindings": [
            {
                "id": item.binding_id,
                "provider": "wechat" if item.provider == "wechat" else "sms" if item.provider == "sms" else "prototype",
                "displayName": item.display_name or item.provider_subject_hint,
                "status": "active" if item.status == "active" else "revoked",
                "boundAtMs": item.bound_at_ms,
                "canUnbind": False,
            }
            for item in user.bindings
        ],
    }


def _release_manifest() -> dict[str, object]:
    published = _published_desktop_manifest()
    if published is not None:
        public_entries: list[dict[str, object]] = []
        for raw_entry in published["entries"]:
            if not isinstance(raw_entry, dict):
                continue
            entry = {key: value for key, value in raw_entry.items() if key != "objectKey"}
            filename = entry.pop("fileName", None)
            if isinstance(filename, str) and filename:
                download_url = f"/api/v1/web/downloads/desktop/{filename}"
                entry["downloadUrl"] = download_url
                entry["localPath"] = download_url
            public_entries.append(entry)
        return {
            "version": int(published.get("version", 1)),
            "generatedAtMs": int(published.get("generatedAtMs", 0)),
            "entries": public_entries,
        }
    now_ms = 1_719_734_400_000
    desktop_release_dir = _desktop_release_dir()
    metadata_files = sorted(
        desktop_release_dir.glob("OfferSteady-Companion-*-macOS-arm64.json"),
        key=lambda item: item.stat().st_mtime if item.exists() else 0,
        reverse=True,
    )
    local_artifacts = sorted(
        [
            *desktop_release_dir.glob("OfferSteady-Companion-*-macOS-arm64.dmg"),
            *desktop_release_dir.glob("OfferSteady-Companion-*-macOS-arm64.zip"),
        ],
        key=lambda item: item.stat().st_mtime if item.exists() else 0,
        reverse=True,
    )
    local_artifact = local_artifacts[0] if local_artifacts else None
    local_sha = "0" * 64
    local_size = 0
    local_path = None
    local_filename = None
    local_version = "0.1.0-dev"
    if metadata_files:
        metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
        zip_path = Path(str(metadata.get("zipPath", "")))
        if zip_path.is_file() and zip_path.resolve().is_relative_to(desktop_release_dir.resolve()):
            local_artifact = zip_path
            local_sha = str(metadata.get("sha256", local_sha))
            local_size = int(metadata.get("fileSizeBytes", zip_path.stat().st_size))
            local_filename = zip_path.name
            local_version = str(metadata.get("version", local_version))
    if local_artifact is not None and local_artifact.is_file():
        if local_filename is None:
            local_bytes = local_artifact.read_bytes()
            local_sha = hashlib.sha256(local_bytes).hexdigest()
            local_size = local_artifact.stat().st_size
            local_filename = local_artifact.name
        local_path = f"/api/v1/web/downloads/desktop/{local_filename}"
    return {
        "version": 1,
        "generatedAtMs": now_ms,
        "entries": [
            {
                "id": "mac-arm64-local-dev",
                "platform": "macos",
                "architecture": "arm64",
                "displayName": "macOS Apple Silicon 本机开发版",
                "version": local_version,
                "minimumOs": "macOS 14.2+",
                "fileSizeBytes": local_size,
                "sha256": local_sha,
                "signingStatus": "local-development",
                "notarized": False,
                "publishedAtMs": now_ms,
                "protocolVersion": "1.0.0",
                "downloadUrl": local_path,
                "localPath": local_path,
                "buildCommand": "npm run package:mac:arm64 -w @offersteady/desktop",
                "developmentOnly": True,
                "capabilities": {"microphone": True, "systemAudio": True, "manualInputFallback": True, "screenshotFallback": True},
            },
            {
                "id": "mac-arm64-010",
                "platform": "macos",
                "architecture": "arm64",
                "displayName": "macOS Apple Silicon",
                "version": "0.1.0",
                "minimumOs": "macOS 14.2+",
                "fileSizeBytes": 82_000_000,
                "sha256": "a" * 64,
                "signingStatus": "pending",
                "notarized": False,
                "publishedAtMs": now_ms,
                "protocolVersion": "1.0.0",
                "buildCommand": "npm run package:mac:arm64 -w @offersteady/desktop",
                "capabilities": {"microphone": True, "systemAudio": True, "manualInputFallback": True, "screenshotFallback": True},
            },
            {
                "id": "mac-x64-010",
                "platform": "macos",
                "architecture": "x64",
                "displayName": "macOS Intel",
                "version": "0.1.0",
                "minimumOs": "macOS 14.2+",
                "fileSizeBytes": 86_000_000,
                "sha256": "b" * 64,
                "signingStatus": "pending",
                "notarized": False,
                "publishedAtMs": now_ms,
                "protocolVersion": "1.0.0",
                "buildCommand": "npm run package:mac:x64 -w @offersteady/desktop",
                "capabilities": {"microphone": True, "systemAudio": True, "manualInputFallback": True, "screenshotFallback": True},
            },
            {
                "id": "win-x64-preview",
                "platform": "windows",
                "architecture": "x64",
                "displayName": "Windows 10/11",
                "version": "0.1.0-preview",
                "minimumOs": "Windows 10 22H2+",
                "fileSizeBytes": 91_000_000,
                "sha256": "c" * 64,
                "signingStatus": "pending",
                "notarized": False,
                "publishedAtMs": now_ms,
                "protocolVersion": "1.0.0",
                "capabilities": {"microphone": True, "systemAudio": False, "manualInputFallback": True, "screenshotFallback": True},
            },
        ],
    }


def _is_selectable_document(document) -> bool:
    return document.status == "ready" and document.index_state == "indexed"


def _artifact_manifest(document, storage: FileStoragePort | None = None, commercial_repository: CommercialHardeningRepository | None = None) -> tuple[str, list[dict[str, object]]]:
    if document.status == "deleted":
        return "deleted", []
    if commercial_repository is not None and document.document_version_id:
        persisted_artifacts = commercial_repository.list_artifacts_for_version(
            owner_user_id=document.owner_user_id,
            document_version_id=document.document_version_id,
        )
        if persisted_artifacts:
            artifacts = [
                {
                    "artifactKind": item.artifact_kind,
                    "objectKey": item.object_key,
                    "exists": item.sync_status == "synced",
                    "required": item.required,
                    "syncStatus": item.sync_status,
                    "verifiedAtMs": item.verified_at_ms,
                    "safeErrorCode": item.safe_error_code,
                }
                for item in persisted_artifacts
            ]
            required = [item for item in persisted_artifacts if item.required]
            if document.status not in {"ready", "failed"}:
                return "processing", artifacts
            if required and not all(item.sync_status == "synced" for item in required):
                return "missing_artifacts", artifacts
            return "synced", artifacts
    key_factory = MaterialObjectKeyFactory(get_settings())
    artifacts: list[dict[str, object]] = []

    def add(kind: str, key: str, *, required: bool = True) -> None:
        artifacts.append({"artifactKind": kind, "objectKey": key, "exists": False, "required": required, "syncStatus": "unknown"})

    if str(document.object_key).startswith("inline://"):
        artifacts.append({"artifactKind": "inline_source", "objectKey": document.object_key, "exists": True, "required": True})
    else:
        add("original", document.object_key, required=True)
    if document.document_version_id:
        add(
            "normalized_markdown",
            key_factory.processed_artifact_key(
                owner_user_id=document.owner_user_id,
                document_kind=document.document_kind,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                artifact_kind="normalized_markdown",
            ),
            required=document.status == "ready",
        )
        add(
            "chunk_manifest",
            key_factory.processed_artifact_key(
                owner_user_id=document.owner_user_id,
                document_kind=document.document_kind,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                artifact_kind="chunk_manifest",
            ),
            required=document.document_kind == "knowledge" or document.status == "ready",
        )
    if document.status not in {"ready", "failed"}:
        return "processing", artifacts
    if document.status == "ready" and document.index_state == "indexed":
        return "synced", artifacts
    if document.status == "failed":
        return "failed", artifacts
    return "missing_artifacts", artifacts


def _document_source_payload(document, storage: FileStoragePort | None = None, commercial_repository: CommercialHardeningRepository | None = None) -> dict[str, object]:
    kind = "jd" if document.document_kind == "job_description" else document.document_kind
    status = {
        "processing_requested": "processing",
        "processing": "processing",
        "ready": "ready",
        "failed": "failed",
        "deleted": "deleted",
    }.get(document.status, "processing")
    sync_status, artifacts = _artifact_manifest(document, storage, commercial_repository)
    selectable = _is_selectable_document(document) and sync_status == "synced"
    safe_summary = document.summary
    if document.document_kind == "resume":
        safe_summary = "简历已处理完成，可在面试准备中选择。"
    elif document.document_kind == "job_description":
        safe_summary = "职位 JD 已处理完成，可在面试准备中选择。"
    return {
        "id": document.document_id,
        "ownerUserId": document.owner_user_id,
        "kind": kind,
        "displayName": document.display_name,
        "version": f"v{document.version or 1}",
        "status": status,
        "processingState": "uploaded" if document.status == "ready" else "processing",
        "updatedAtMs": document.updated_at_ms,
        "summary": safe_summary,
        "documentId": document.document_id,
        "documentVersionId": document.document_version_id,
        "indexState": document.index_state,
        "selectable": selectable,
        "syncStatus": sync_status,
        "artifactManifest": artifacts,
        "unavailableReason": None if selectable else "资料处理产物未同步或尚不可用",
        "deletedAtMs": document.deleted_at_ms,
    }


def _prepared_resource_payload(document) -> dict[str, object]:
    kind = "jd" if document.document_kind == "job_description" else document.document_kind
    status = {
        "processing_requested": "processing",
        "processing": "processing",
        "ready": "ready",
        "failed": "error",
        "deleted": "deleted",
    }.get(document.status, "processing")
    safe_summary = document.summary or ""
    if document.document_kind == "resume":
        safe_summary = "简历已处理完成，可在面试准备中选择。"
    elif document.document_kind == "job_description":
        safe_summary = "职位 JD 已处理完成，可在面试准备中选择。"
    return {
        "id": document.document_id,
        "kind": kind,
        "name": document.display_name,
        "status": status,
        "summary": safe_summary,
        "reusable": document.document_kind != "job_description",
        "documentVersionId": document.document_version_id,
        "indexState": document.index_state,
    }


def _session_status(status: str) -> str:
    if status == "live":
        return "active"
    return status


def _session_payload(session) -> dict[str, object]:
    return {
        "id": session.session_id,
        "title": session.title,
        "role": session.title,
        "status": _session_status(session.status),
        "updatedAt": "刚刚",
        "readiness": 100 if session.material_binding.confirmed_at_ms else 0,
    }


def _selection_payload(session) -> dict[str, object]:
    binding = session.material_binding
    return {
        "sessionId": session.session_id,
        "resumeSourceId": binding.resume_document_id,
        "jobDescriptionSourceId": binding.job_description_document_id,
        "knowledgeSourceIds": binding.knowledge_document_ids,
        "revision": binding.revision,
        "confirmedAtMs": binding.confirmed_at_ms,
        "materialSnapshots": [
            {
                "sourceId": document.document_id,
                "documentId": document.document_id,
                "documentVersionId": document.document_version_id,
                "displayName": document.display_name,
                "kind": "jd" if document.document_kind == "job_description" else document.document_kind,
                "indexState": document.index_state,
                "active": document.active,
            }
            for document in binding.bound_documents
        ],
    }


def _question_from_chat(task) -> dict[str, object]:
    status = "cancelled" if task.status == "cancelled" else "failed" if task.status == "failed" else "confirmed" if task.status == "completed" else "generating"
    return {
        "id": task.task_id,
        "askedAt": "刚刚",
        "text": task.question,
        "input": "manual",
        "status": status,
        "advice": {
            "outline": [],
            "detail": task.answer_text or "回答正在生成，完成后会在这里展示。",
            "sourceTypes": ["简历", "JD", "知识库"],
            "inference": "",
            "uncertain": task.status == "failed",
            "provenance": {"selectionRevision": 0, "usedSources": []},
        },
    }


def _question_from_screenshot(task) -> dict[str, object]:
    status = "failed" if task.status == "failed" else "confirmed" if task.status == "completed" else "generating"
    return {
        "id": task.task_id,
        "askedAt": "刚刚",
        "text": task.instruction or task.vision_summary_title or "截图回答",
        "input": "screenshot",
        "status": status,
        "advice": {
            "outline": [],
            "detail": task.answer_text or "截图回答正在生成，完成后会在这里展示。",
            "sourceTypes": ["简历", "JD", "知识库"],
            "inference": "",
            "uncertain": task.status == "failed",
            "provenance": {"selectionRevision": 0, "usedSources": []},
        },
    }


def _knowledge_collection_payload(collection) -> dict[str, object]:
    return {
        "id": collection.collection_id,
        "ownerUserId": collection.owner_user_id,
        "name": collection.name,
        "createdAtMs": collection.created_at_ms,
        "updatedAtMs": collection.updated_at_ms,
    }


def _knowledge_document_payload(document, storage: FileStoragePort | None = None, commercial_repository: CommercialHardeningRepository | None = None) -> dict[str, object]:
    status = "ready" if document.status == "ready" else "failed" if document.status == "failed" else "deleted" if document.status == "deleted" else "processing"
    sync_status, artifacts = _artifact_manifest(document, storage, commercial_repository)
    selectable = _is_selectable_document(document) and sync_status == "synced"
    return {
        "id": document.document_id,
        "collectionId": document.knowledge_collection_id or "default",
        "ownerUserId": document.owner_user_id,
        "displayName": document.display_name,
        "fileKind": document.file_kind,
        "sizeBytes": document.size_bytes,
        "contentFingerprint": document.content_fingerprint,
        "documentVersionId": document.document_version_id,
        "indexState": document.index_state,
        "version": document.version or 1,
        "status": status,
        "selectable": selectable,
        "syncStatus": sync_status,
        "artifactManifest": artifacts,
        "unavailableReason": None if selectable else "资料处理产物未同步或尚不可用",
        "createdAtMs": document.created_at_ms,
        "deletedAtMs": document.deleted_at_ms,
        "safeSummary": document.summary,
    }


@router.get("/state", response_model=ApiEnvelope[dict[str, object]])
async def get_web_state(
    request: Request,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    documents: DocumentService = Depends(document_read_service),
    billing: BillingService = Depends(billing_service),
    sessions: SessionService = Depends(session_service),
) -> ApiEnvelope[dict[str, object]]:
    user = authentication_service().get_current_user(auth_context=auth_context) if auth_context else None
    settings = get_settings()
    user_id = auth_context.user_id if auth_context else settings.development_user_id
    account = _account_payload(user)
    billing_state = billing.state_for_user(user_id=user_id)
    document_items = documents.list_documents(user_id=user_id, include_deleted=False)
    session_items = sessions.list_sessions(user_id=user_id) if auth_context else []
    chat_questions: list[dict[str, object]] = []
    screenshot_questions: list[dict[str, object]] = []
    review_screenshots: list[dict[str, object]] = []
    resources = [_prepared_resource_payload(item) for item in document_items[:3]]
    state = {
        "interviews": [_session_payload(item) for item in session_items],
        "preparation": {"resources": resources, "device": None},
        "questions": [*chat_questions, *screenshot_questions],
        "review": {
            "status": "complete" if chat_questions or screenshot_questions else "waiting",
            "duration": "0 分钟",
            "summary": "暂无可复盘记录。" if not chat_questions and not screenshot_questions else "已从后端会话记录整理本场问题与回答。",
            "screenshots": review_screenshots,
        },
        "captureState": "ready",
        "librarySources": [_document_source_payload(item, None, None) for item in document_items],
        "contextSelections": {item.session_id: _selection_payload(item) for item in session_items},
        "billing": billing.state_payload(billing_state),
        "speaker": {"mode": "dual-channel", "transcripts": [], "pendingQuestion": None, "degradation": None},
        "activeAnswerTask": None,
        "account": account,
        "knowledgeCollections": [
            _knowledge_collection_payload(item)
            for item in documents.knowledge_store.collections.values()
            if user_id and item.owner_user_id == user_id
        ],
        "knowledgeDocuments": [_knowledge_document_payload(item, None, None) for item in document_items if item.document_kind == "knowledge"],
        "releaseManifest": _release_manifest(),
    }
    return success_response(request=request, data=state, timestamp=utc_now_iso())
