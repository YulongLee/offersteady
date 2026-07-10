from __future__ import annotations

from time import time
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.document_repository import DocumentRepository
from app.ports.interview_session import (
    ConversationContextEntry,
    IntegrationReference,
    InterviewSessionRecord,
    InterviewSessionRepository,
    SessionBoundDocument,
    SessionConfigSnapshot,
    SessionContinueTarget,
    SessionMaterialBinding,
    SessionUsageRecord,
    SessionUsageTotals,
)
from app.services.material_availability import MaterialAvailabilityValidator


def _now_ms() -> int:
    return int(time() * 1000)


class SessionService:
    def __init__(
        self,
        *,
        settings: Settings,
        document_repository: DocumentRepository,
        repository: InterviewSessionRepository,
        material_availability: MaterialAvailabilityValidator | None = None,
    ) -> None:
        self.settings = settings
        self.document_repository = document_repository
        self.repository = repository
        self.material_availability = material_availability

    def create_session(self, *, user_id: str, title: str, restart_of_session_id: str | None = None) -> InterviewSessionRecord:
        now_ms = _now_ms()
        session_id = f"session-{uuid4().hex}"
        config_snapshot = self._default_config_snapshot(captured_at_ms=now_ms)
        material_binding = SessionMaterialBinding(
            session_id=session_id,
            owner_user_id=user_id,
            revision=0,
            resume_document_id=None,
            job_description_document_id=None,
            knowledge_document_ids=[],
            bound_documents=[],
            confirmed_at_ms=None,
        )
        session = InterviewSessionRecord(
            session_id=session_id,
            owner_user_id=user_id,
            title=title.strip(),
            status="preparing",
            continue_target="preparing",
            material_binding=material_binding,
            config_snapshot=config_snapshot,
            usage_totals=SessionUsageTotals(),
            integration_references=self._build_integration_references(
                session_id=session_id,
                user_id=user_id,
                material_binding=material_binding,
            ),
            restart_of_session_id=restart_of_session_id,
            started_at_ms=None,
            ended_at_ms=None,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            last_activity_at_ms=now_ms,
        )
        return self.repository.save_session(session)

    def list_sessions(self, *, user_id: str, status: str | None = None) -> list[InterviewSessionRecord]:
        sessions = self.repository.list_sessions_for_user(user_id=user_id, status=status)  # type: ignore[arg-type]
        return [self._refresh_bound_document_activity(session) for session in sessions]

    def delete_session(self, *, user_id: str, session_id: str) -> None:
        session = self.get_session(user_id=user_id, session_id=session_id)
        deleted = self.repository.delete_session(user_id=user_id, session_id=session.session_id)
        if not deleted:
            raise DomainRequestError("session", "delete", "面试会话不存在或已被删除。", 404)

    def get_session(self, *, user_id: str, session_id: str) -> InterviewSessionRecord:
        session = self.repository.get_session(session_id)
        if session is None:
            raise DomainRequestError("session", "get", "面试会话不存在。", 404)
        if session.owner_user_id != user_id:
            raise DomainRequestError("session", "get", "不能查看其他用户的面试会话。", 403)
        refreshed = self._refresh_bound_document_activity(session)
        if refreshed != session:
            self.repository.save_session(refreshed)
        return refreshed

    def continue_session(self, *, user_id: str, session_id: str) -> InterviewSessionRecord:
        return self.get_session(user_id=user_id, session_id=session_id)

    def confirm_materials(
        self,
        *,
        user_id: str,
        session_id: str,
        resume_document_id: str | None,
        job_description_document_id: str | None,
        knowledge_document_ids: list[str],
    ) -> InterviewSessionRecord:
        session = self.get_session(user_id=user_id, session_id=session_id)
        if session.status == "ended":
            raise DomainRequestError("session", "confirm-materials", "已结束的会话不能再修改本场资料。", 400)
        bound_documents: list[SessionBoundDocument] = []
        if resume_document_id:
            bound_documents.append(self._require_document(user_id=user_id, document_id=resume_document_id, expected_kind="resume"))
        if job_description_document_id:
            bound_documents.append(self._require_document(user_id=user_id, document_id=job_description_document_id, expected_kind="job_description"))
        for document_id in knowledge_document_ids:
            bound_documents.append(self._require_document(user_id=user_id, document_id=document_id, expected_kind="knowledge"))
        now_ms = _now_ms()
        material_binding = SessionMaterialBinding(
            session_id=session.session_id,
            owner_user_id=user_id,
            revision=session.material_binding.revision + 1,
            resume_document_id=resume_document_id,
            job_description_document_id=job_description_document_id,
            knowledge_document_ids=list(dict.fromkeys(knowledge_document_ids)),
            bound_documents=bound_documents,
            confirmed_at_ms=now_ms,
        )
        updated = self._save_session(
            session,
            material_binding=material_binding,
            updated_at_ms=now_ms,
            last_activity_at_ms=now_ms,
            integration_references=self._build_integration_references(
                session_id=session.session_id,
                user_id=user_id,
                material_binding=material_binding,
            ),
        )
        return updated

    def start_session(self, *, user_id: str, session_id: str) -> InterviewSessionRecord:
        session = self.get_session(user_id=user_id, session_id=session_id)
        if session.status == "ended":
            raise DomainRequestError("session", "start", "已结束的会话不能直接开始，请重新开始一场新的面试。", 400)
        now_ms = _now_ms()
        return self._save_session(
            session,
            status="live",
            continue_target="live",
            started_at_ms=session.started_at_ms or now_ms,
            updated_at_ms=now_ms,
            last_activity_at_ms=now_ms,
        )

    def end_session(self, *, user_id: str, session_id: str) -> InterviewSessionRecord:
        session = self.get_session(user_id=user_id, session_id=session_id)
        now_ms = _now_ms()
        return self._save_session(
            session,
            status="ended",
            continue_target="history",
            ended_at_ms=now_ms,
            updated_at_ms=now_ms,
            last_activity_at_ms=now_ms,
        )

    def restart_session(self, *, user_id: str, session_id: str) -> InterviewSessionRecord:
        session = self.get_session(user_id=user_id, session_id=session_id)
        restarted = self.create_session(user_id=user_id, title=f"{session.title} · 重新开始", restart_of_session_id=session.session_id)
        if session.material_binding.confirmed_at_ms is not None:
            restarted = self.confirm_materials(
                user_id=user_id,
                session_id=restarted.session_id,
                resume_document_id=session.material_binding.resume_document_id,
                job_description_document_id=session.material_binding.job_description_document_id,
                knowledge_document_ids=session.material_binding.knowledge_document_ids,
            )
        restarted = self._save_session(
            restarted,
            config_snapshot=session.config_snapshot,
            updated_at_ms=_now_ms(),
            last_activity_at_ms=_now_ms(),
        )
        return restarted

    def append_context(
        self,
        *,
        user_id: str,
        session_id: str,
        role: str,
        source_kind: str,
        content: str,
        visibility: str,
        related_task_id: str | None = None,
    ) -> ConversationContextEntry:
        session = self.get_session(user_id=user_id, session_id=session_id)
        if session.status == "ended":
            raise DomainRequestError("session", "append-context", "已结束的会话不能继续追加上下文。", 400)
        now_ms = _now_ms()
        entry = ConversationContextEntry(
            entry_id=f"context-{uuid4().hex}",
            session_id=session_id,
            owner_user_id=user_id,
            role=role,  # type: ignore[arg-type]
            source_kind=source_kind,
            content=content.strip(),
            visibility=visibility,  # type: ignore[arg-type]
            ordering=len(self.repository.list_context_entries(session_id=session_id)) + 1,
            related_task_id=related_task_id,
            created_at_ms=now_ms,
        )
        stored = self.repository.append_context_entry(entry)
        self._save_session(session, updated_at_ms=now_ms, last_activity_at_ms=now_ms)
        return stored

    def get_context_window(self, *, user_id: str, session_id: str, limit: int | None = None) -> list[ConversationContextEntry]:
        self.get_session(user_id=user_id, session_id=session_id)
        entries = self.repository.list_context_entries(session_id=session_id)
        if limit is None or limit <= 0:
            return entries
        return entries[-limit:]

    def record_usage(
        self,
        *,
        user_id: str,
        session_id: str,
        usage_kind: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        provider_name: str | None,
        model_name: str | None,
        related_task_id: str | None = None,
    ) -> InterviewSessionRecord:
        session = self.get_session(user_id=user_id, session_id=session_id)
        now_ms = _now_ms()
        effective_total = total_tokens or (prompt_tokens + completion_tokens)
        record = SessionUsageRecord(
            usage_id=f"usage-{uuid4().hex}",
            session_id=session_id,
            owner_user_id=user_id,
            usage_kind=usage_kind,  # type: ignore[arg-type]
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=effective_total,
            provider_name=provider_name,
            model_name=model_name,
            related_task_id=related_task_id,
            created_at_ms=now_ms,
        )
        self.repository.save_usage_record(record)
        totals = self._calculate_usage_totals(session_id=session_id)
        return self._save_session(session, usage_totals=totals, updated_at_ms=now_ms, last_activity_at_ms=now_ms)

    def get_usage(self, *, user_id: str, session_id: str) -> tuple[SessionUsageTotals, list[SessionUsageRecord]]:
        self.get_session(user_id=user_id, session_id=session_id)
        records = self.repository.list_usage_records(session_id=session_id)
        return self._calculate_usage_totals(session_id=session_id), records

    def _calculate_usage_totals(self, *, session_id: str) -> SessionUsageTotals:
        prompt = completion = total = embedding = retrieval = 0
        records = self.repository.list_usage_records(session_id=session_id)
        for record in records:
            prompt += record.prompt_tokens
            completion += record.completion_tokens
            total += record.total_tokens
            if record.usage_kind == "embedding":
                embedding += record.total_tokens
            if record.usage_kind == "retrieval":
                retrieval += record.total_tokens
        return SessionUsageTotals(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            embedding_tokens=embedding,
            retrieval_tokens=retrieval,
            record_count=len(records),
        )

    def _require_document(self, *, user_id: str, document_id: str, expected_kind: str) -> SessionBoundDocument:
        record = self.document_repository.get_by_id(document_id)
        if record is None:
            raise DomainRequestError("session", "confirm-materials", "所选资料不存在。", 404)
        if record.owner_user_id != user_id:
            raise DomainRequestError("session", "confirm-materials", "不能选择其他用户的资料。", 403)
        if record.document_kind != expected_kind:
            raise DomainRequestError("session", "confirm-materials", "资料类型与当前分组不匹配。", 400)
        if record.status != "ready" or record.index_state not in {None, "indexed"}:
            raise DomainRequestError("session", "confirm-materials", "只有已就绪资料才能加入本场面试。", 400)
        return SessionBoundDocument(
            document_id=record.document_id,
            document_kind=record.document_kind,
            display_name=record.display_name,
            status=record.status,
            document_version_id=record.document_version_id,
            index_state=record.index_state,
            knowledge_collection_id=record.knowledge_collection_id,
            summary=record.summary,
            active=True,
        )

    def _refresh_bound_document_activity(self, session: InterviewSessionRecord) -> InterviewSessionRecord:
        refreshed_docs: list[SessionBoundDocument] = []
        changed = False
        for bound in session.material_binding.bound_documents:
            current = self.document_repository.get_by_id(bound.document_id)
            active = current is not None and current.status == "ready" and current.index_state in {None, "indexed"}
            status = current.status if current is not None else "deleted"
            display_name = current.display_name if current is not None else bound.display_name
            summary = current.summary if current is not None else bound.summary
            knowledge_collection_id = current.knowledge_collection_id if current is not None else bound.knowledge_collection_id
            document_version_id = current.document_version_id if current is not None else bound.document_version_id
            index_state = current.index_state if current is not None else "deleted"
            refreshed = SessionBoundDocument(
                document_id=bound.document_id,
                document_kind=bound.document_kind,
                display_name=display_name,
                status=status,
                document_version_id=document_version_id,
                index_state=index_state,
                knowledge_collection_id=knowledge_collection_id,
                summary=summary,
                active=active,
            )
            if refreshed != bound:
                changed = True
            refreshed_docs.append(refreshed)
        if not changed:
            return session
        binding = SessionMaterialBinding(
            session_id=session.material_binding.session_id,
            owner_user_id=session.material_binding.owner_user_id,
            revision=session.material_binding.revision,
            resume_document_id=session.material_binding.resume_document_id,
            job_description_document_id=session.material_binding.job_description_document_id,
            knowledge_document_ids=session.material_binding.knowledge_document_ids,
            bound_documents=refreshed_docs,
            confirmed_at_ms=session.material_binding.confirmed_at_ms,
        )
        return self._save_session(
            session,
            material_binding=binding,
            integration_references=self._build_integration_references(
                session_id=session.session_id,
                user_id=session.owner_user_id,
                material_binding=binding,
            ),
            updated_at_ms=session.updated_at_ms,
            last_activity_at_ms=session.last_activity_at_ms,
        )

    def _default_config_snapshot(self, *, captured_at_ms: int) -> SessionConfigSnapshot:
        return SessionConfigSnapshot(
            model_config_ref=f"model/default@{self.settings.app_version}",
            prompt_config_ref=f"prompt/default@{self.settings.app_version}",
            retrieval_config_ref=f"retrieval/{self.settings.retrieval_strategy}@{self.settings.app_version}",
            version_tag=self.settings.app_version,
            captured_at_ms=captured_at_ms,
        )

    def _build_integration_references(
        self,
        *,
        session_id: str,
        user_id: str,
        material_binding: SessionMaterialBinding,
    ) -> list[IntegrationReference]:
        knowledge_collection_ids = [
            doc.knowledge_collection_id
            for doc in material_binding.bound_documents
            if doc.document_kind == "knowledge" and doc.knowledge_collection_id
        ]
        document_ids = [doc.document_id for doc in material_binding.bound_documents if doc.active]
        document_version_ids = [doc.document_version_id for doc in material_binding.bound_documents if doc.active and doc.document_version_id]
        return [
            IntegrationReference(
                name="knowledge-retrieval",
                session_id=session_id,
                details={
                    "ownerUserId": user_id,
                    "interviewSessionId": session_id,
                    "documentIds": document_ids,
                    "documentVersionIds": document_version_ids,
                    "knowledgeCollectionIds": knowledge_collection_ids,
                },
            ),
            IntegrationReference(name="answer-generation", session_id=session_id, details={"sessionState": "authoritative"}),
            IntegrationReference(name="screenshot-answer", session_id=session_id, details={"sessionScoped": True}),
            IntegrationReference(name="desktop-bridge", session_id=session_id, details={"authorizedBySession": True}),
            IntegrationReference(name="billing", session_id=session_id, details={"usageTrackedAtSessionScope": True}),
        ]

    def _save_session(self, session: InterviewSessionRecord, **updates) -> InterviewSessionRecord:
        updated = InterviewSessionRecord(
            session_id=updates.get("session_id", session.session_id),
            owner_user_id=updates.get("owner_user_id", session.owner_user_id),
            title=updates.get("title", session.title),
            status=updates.get("status", session.status),
            continue_target=updates.get("continue_target", self._derive_continue_target(updates.get("status", session.status))),
            material_binding=updates.get("material_binding", session.material_binding),
            config_snapshot=updates.get("config_snapshot", session.config_snapshot),
            usage_totals=updates.get("usage_totals", session.usage_totals),
            integration_references=updates.get("integration_references", session.integration_references),
            restart_of_session_id=updates.get("restart_of_session_id", session.restart_of_session_id),
            started_at_ms=updates.get("started_at_ms", session.started_at_ms),
            ended_at_ms=updates.get("ended_at_ms", session.ended_at_ms),
            created_at_ms=updates.get("created_at_ms", session.created_at_ms),
            updated_at_ms=updates.get("updated_at_ms", session.updated_at_ms),
            last_activity_at_ms=updates.get("last_activity_at_ms", session.last_activity_at_ms),
        )
        return self.repository.save_session(updated)

    def _derive_continue_target(self, status: str) -> SessionContinueTarget:
        if status == "live":
            return "live"
        if status == "ended":
            return "history"
        return "preparing"
