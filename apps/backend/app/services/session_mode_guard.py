"""Keep dedicated mock-interview commands out of legacy billing and AI paths."""
from app.core.errors import DomainRequestError
from app.ports.interview_session import InterviewSessionRecord


def require_standard_session(session: InterviewSessionRecord) -> None:
    # Older standard-session adapters omit this field; their established default
    # is interview. Mock records always have an explicit persisted mode.
    if getattr(session, "session_mode", "interview") == "mock":
        raise DomainRequestError(
            "mock-interview", "legacy-command",
            "请在 AI 模拟面试页面操作，该场次不支持普通面试指令。",
            409, "mock_dedicated_command_required",
        )
