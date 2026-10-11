"""Network-free, synthetic-only smoke checks inside the candidate image."""
from dataclasses import replace
import json
import sys
import threading
from time import time
from unittest.mock import Mock

sys.path.insert(0, "/app/apps/backend")
from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.interview_session import SessionBoundDocument
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.session_service import SessionService


def main():
    checks = 0
    now = int(time()*1000)
    settings = Settings(_env_file=None, database_url=None, redis_url=None,
        interview_idle_warning_seconds=60, interview_idle_timeout_seconds=120)
    repository = InMemoryInterviewSessionRepository()
    documents = Mock()
    documents.get_by_id.return_value = None
    sessions = SessionService(settings=settings, repository=repository, document_repository=documents)
    created = sessions.create_session(user_id="synthetic-probe-owner", title="Synthetic candidate probe")
    record = replace(created, status="live", started_at_ms=now,
        material_binding=replace(created.material_binding, bound_documents=[
            SessionBoundDocument(document_id="synthetic-doc", document_kind="knowledge", display_name="Synthetic", status="ready")]))
    repository.save_session(record)
    service = object.__new__(RealtimeSpeechService)
    service.settings, service.session_service = settings, sessions
    service.repository = InMemoryRealtimeSpeechRepository()
    service._session_activity_lock = threading.Lock()
    service._session_last_activity_ms, service._session_owners = {}, {}
    service.terminate_session_for_admin = Mock()
    full_read = repository.get_session
    repository.get_session = Mock(side_effect=AssertionError("full read on heartbeat"))
    original_projection = repository.get_heartbeat_state
    repository.get_heartbeat_state = Mock(wraps=original_projection)

    def beat(user=record.owner_user_id, page="live", instance="synthetic-page"):
        return service.record_web_session_heartbeat(user_id=user, session_id=record.session_id,
            binding_id=None, page=page, page_instance_id=instance)

    first = beat()
    assert first.session_id == record.session_id and first.lease_expires_at_ms > now
    repository.get_heartbeat_state.assert_called_once()
    documents.get_by_id.assert_not_called(); checks += 1
    assert beat(page="preparation", instance=None).page_instance_id == "synthetic-page"; checks += 1
    assert beat().lease_generation == first.lease_generation; checks += 1
    assert beat(instance="synthetic-page-b").page_instance_id == "synthetic-page-b"; checks += 1
    for status in ("preparing", "live", "ended"):
        repository.save_session(replace(record, status=status, started_at_ms=None if status=="preparing" else now))
        for offset, expected in ((59_999,"active"),(60_000,"warning"),(120_000,"expired")):
            actual = sessions.heartbeat_idle_status(user_id=record.owner_user_id, session_id=record.session_id, at_ms=record.last_activity_at_ms+offset)
            assert actual["state"] == ("ended" if status=="ended" else "active" if status=="preparing" else expected)
        checks += 1
    try: beat()
    except DomainRequestError as exc: assert exc.status_code == 409
    else: raise AssertionError("ended accepted")
    checks += 1
    repository.save_session(record)
    owners_before = dict(service._session_owners)
    try: beat(user="synthetic-other-owner")
    except DomainRequestError as exc: assert exc.status_code == 403
    else: raise AssertionError("wrong owner accepted")
    assert service._session_owners == owners_before; checks += 1
    repository.save_session(replace(record, last_activity_at_ms=now-120_001))
    try: beat()
    except DomainRequestError as exc: assert exc.error_code == "realtime_session_ended"
    else: raise AssertionError("expired accepted")
    service.terminate_session_for_admin.assert_called_once_with(user_id=record.owner_user_id, session_id=record.session_id, reason="idle-timeout"); checks += 1
    repository.save_session(record)
    repository.get_session = full_read
    refreshed = sessions.get_session(user_id=record.owner_user_id, session_id=record.session_id)
    assert not refreshed.material_binding.bound_documents[0].active; checks += 1
    repository.sessions.clear()
    try: beat()
    except DomainRequestError as exc: assert exc.status_code == 404
    else: raise AssertionError("missing accepted")
    checks += 1
    print(json.dumps({"passed":True,"checks":checks,"syntheticOnly":True,"networkRequired":False}))


if __name__ == "__main__":
    main()
