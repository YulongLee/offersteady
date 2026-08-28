from dataclasses import asdict
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.schemas.session import CreateInterviewSessionRequest, UpdateInterviewProgrammingRequest
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.programming_prompt import render_programming_policy
from app.services.session_service import SessionService


class EmptyDocumentRepository:
    def get_by_id(self, document_id):
        return None


def make_service():
    repository = InMemoryInterviewSessionRepository()
    return SessionService(settings=Settings(_env_file=None), document_repository=EmptyDocumentRepository(), repository=repository), repository


def test_legacy_session_defaults_to_no_programming() -> None:
    service, repository = make_service()
    created = service.create_session(user_id="synthetic-owner", title="Synthetic interview")
    request = CreateInterviewSessionRequest(userId="synthetic-owner", title="Legacy request")

    assert created.programming_required is False
    assert created.programming_language is None
    assert repository.get_session(created.session_id).programming_language is None
    assert request.programming_required is False and request.programming_language is None


def test_preparing_owner_can_select_language_and_restart_inherits_it() -> None:
    service, _ = make_service()
    created = service.create_session(user_id="synthetic-owner", title="Synthetic interview")
    updated = service.update_interview_programming(
        user_id="synthetic-owner", session_id=created.session_id,
        programming_required=True, programming_language="java",
    )
    service.start_session(user_id="synthetic-owner", session_id=created.session_id)
    ended = service.end_session(user_id="synthetic-owner", session_id=created.session_id)
    restarted = service.restart_session(user_id="synthetic-owner", session_id=ended.session_id)

    assert updated.programming_required is True and updated.programming_language == "java"
    assert restarted.status == "preparing"
    assert restarted.programming_required is True and restarted.programming_language == "java"


def test_programming_update_is_owner_only_and_locked_after_start() -> None:
    service, _ = make_service()
    created = service.create_session(user_id="synthetic-owner", title="Synthetic interview")
    with pytest.raises(DomainRequestError) as forbidden:
        service.update_interview_programming(
            user_id="another-user", session_id=created.session_id,
            programming_required=True, programming_language="go",
        )
    assert forbidden.value.status_code == 403

    service.start_session(user_id="synthetic-owner", session_id=created.session_id)
    with pytest.raises(DomainRequestError) as locked:
        service.update_interview_programming(
            user_id="synthetic-owner", session_id=created.session_id,
            programming_required=True, programming_language="go",
        )
    assert locked.value.error_code == "interview_programming_locked"


def test_request_normalizes_default_python_and_rejects_invalid_combinations() -> None:
    enabled = UpdateInterviewProgrammingRequest(userId="synthetic-owner", programmingRequired=True)
    assert enabled.programming_language == "python"
    with pytest.raises(ValidationError):
        UpdateInterviewProgrammingRequest(
            userId="synthetic-owner", programmingRequired=False, programmingLanguage="java"
        )
    with pytest.raises(ValidationError):
        UpdateInterviewProgrammingRequest(
            userId="synthetic-owner", programmingRequired=True, programmingLanguage="rust"
        )


def test_postgres_mapping_and_migration_round_trip_programming_preference() -> None:
    service, _ = make_service()
    session = service.create_session(
        user_id="synthetic-owner", title="Synthetic interview",
        programming_required=True, programming_language="typescript",
    )
    row = {
        "session_id": session.session_id, "owner_user_id": session.owner_user_id,
        "title": session.title, "interview_language": "zh-CN",
        "programming_required": True, "programming_language": "typescript",
        "status": session.status, "continue_target": session.continue_target,
        "material_binding_json": asdict(session.material_binding),
        "config_snapshot_json": asdict(session.config_snapshot),
        "usage_totals_json": asdict(session.usage_totals),
        "integration_references_json": [], "restart_of_session_id": None,
        "started_at_ms": None, "ended_at_ms": None,
        "created_at_ms": session.created_at_ms, "updated_at_ms": session.updated_at_ms,
        "last_activity_at_ms": session.last_activity_at_ms,
    }
    repository = object.__new__(PostgresInterviewSessionRepository)
    mapped = repository._row_to_session(row)
    migration = (Path(__file__).parents[1] / "migrations/versions/0034_interview_programming_preference.sql").read_text(encoding="utf8")

    assert mapped.programming_required is True and mapped.programming_language == "typescript"
    assert "programming_required BOOLEAN NOT NULL DEFAULT FALSE" in migration
    assert "'python', 'java', 'cpp', 'javascript', 'typescript', 'go'" in migration


@pytest.mark.parametrize(
    ("language", "label", "fence"),
    [("python", "Python", "python"), ("java", "Java", "java"), ("cpp", "C++", "cpp"),
     ("javascript", "JavaScript", "javascript"), ("typescript", "TypeScript", "typescript"), ("go", "Go", "go")],
)
def test_programming_policy_renders_closed_language(language, label, fence) -> None:
    policy = render_programming_policy(
        programming_required=True, programming_language=language, interview_language="zh-CN"
    )
    assert label in policy
    assert f"```{fence}" in policy
    assert "非代码题正常回答" in policy


def test_disabled_programming_policy_preserves_existing_prompt_behavior() -> None:
    assert render_programming_policy(
        programming_required=False, programming_language=None, interview_language="zh-CN"
    ) == ""
