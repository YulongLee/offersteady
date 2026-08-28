from __future__ import annotations

from dataclasses import replace
from threading import RLock

from app.ports.interview_session import (
    ConversationContextEntry,
    InterviewSessionRecord,
    InterviewSessionRepository,
    InterviewLanguage,
    ProgrammingLanguage,
    SessionUsageRecord,
)


class InMemoryInterviewSessionRepository(InterviewSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[str, InterviewSessionRecord] = {}
        self.context_entries: dict[str, list[ConversationContextEntry]] = {}
        self.usage_records: dict[str, list[SessionUsageRecord]] = {}
        self._session_lock = RLock()

    def save_session(self, session: InterviewSessionRecord) -> InterviewSessionRecord:
        stored = replace(session)
        self.sessions[stored.session_id] = stored
        return replace(stored)

    def get_session(self, session_id: str) -> InterviewSessionRecord | None:
        record = self.sessions.get(session_id)
        return replace(record) if record else None

    def list_sessions_for_user(self, *, user_id: str, status=None) -> list[InterviewSessionRecord]:
        items = [session for session in self.sessions.values() if session.owner_user_id == user_id]
        if status is not None:
            items = [session for session in items if session.status == status]
        return [replace(item) for item in sorted(items, key=lambda item: item.updated_at_ms, reverse=True)]

    def touch_activity(self, *, user_id: str, session_id: str, activity_at_ms: int) -> InterviewSessionRecord | None:
        session = self.sessions.get(session_id)
        if session is None or session.owner_user_id != user_id or session.status == "ended":
            return replace(session) if session is not None and session.owner_user_id == user_id else None
        touched = replace(session, updated_at_ms=activity_at_ms, last_activity_at_ms=activity_at_ms)
        self.sessions[session_id] = touched
        return replace(touched)

    def update_language_if_preparing(
        self, *, user_id: str, session_id: str, interview_language: InterviewLanguage, updated_at_ms: int
    ) -> InterviewSessionRecord | None:
        with self._session_lock:
            session = self.sessions.get(session_id)
            if session is None or session.owner_user_id != user_id or session.status != "preparing":
                return None
            updated = replace(
                session,
                interview_language=interview_language,
                updated_at_ms=updated_at_ms,
                last_activity_at_ms=updated_at_ms,
            )
            self.sessions[session_id] = updated
            return replace(updated)

    def update_programming_if_preparing(
        self, *, user_id: str, session_id: str, programming_required: bool,
        programming_language: ProgrammingLanguage | None, updated_at_ms: int
    ) -> InterviewSessionRecord | None:
        with self._session_lock:
            session = self.sessions.get(session_id)
            if session is None or session.owner_user_id != user_id or session.status != "preparing":
                return None
            updated = replace(
                session,
                programming_required=programming_required,
                programming_language=programming_language,
                updated_at_ms=updated_at_ms,
                last_activity_at_ms=updated_at_ms,
            )
            self.sessions[session_id] = updated
            return replace(updated)

    def start_if_not_ended(
        self, *, user_id: str, session_id: str, started_at_ms: int
    ) -> InterviewSessionRecord | None:
        with self._session_lock:
            session = self.sessions.get(session_id)
            if session is None or session.owner_user_id != user_id or session.status == "ended":
                return None
            updated = replace(
                session,
                status="live",
                continue_target="live",
                started_at_ms=session.started_at_ms or started_at_ms,
                updated_at_ms=started_at_ms,
                last_activity_at_ms=started_at_ms,
            )
            self.sessions[session_id] = updated
            return replace(updated)

    def list_idle_live_sessions(self, *, before_ms: int, limit: int, user_id: str | None = None) -> list[InterviewSessionRecord]:
        items = [
            session for session in self.sessions.values()
            if session.status == "live"
            and session.last_activity_at_ms < before_ms
            and (user_id is None or session.owner_user_id == user_id)
        ]
        return [replace(item) for item in sorted(items, key=lambda item: item.last_activity_at_ms)[:limit]]

    def delete_session(self, *, user_id: str, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session is None or session.owner_user_id != user_id:
            return False
        self.sessions.pop(session_id, None)
        self.context_entries.pop(session_id, None)
        self.usage_records.pop(session_id, None)
        return True

    def append_context_entry(self, entry: ConversationContextEntry) -> ConversationContextEntry:
        stored = replace(entry)
        entries = self.context_entries.setdefault(stored.session_id, [])
        entries.append(stored)
        entries.sort(key=lambda item: (item.ordering, item.created_at_ms, item.entry_id))
        return replace(stored)

    def list_context_entries(self, *, session_id: str) -> list[ConversationContextEntry]:
        return [replace(item) for item in self.context_entries.get(session_id, [])]

    def save_usage_record(self, record: SessionUsageRecord) -> SessionUsageRecord:
        stored = replace(record)
        entries = self.usage_records.setdefault(stored.session_id, [])
        entries.append(stored)
        entries.sort(key=lambda item: (item.created_at_ms, item.usage_id))
        return replace(stored)

    def list_usage_records(self, *, session_id: str) -> list[SessionUsageRecord]:
        return [replace(item) for item in self.usage_records.get(session_id, [])]
