"""Legacy entry points must reject mock mode before charging or doing AI work."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.core.errors import DomainRequestError
from app.schemas.session import CreateInterviewSessionRequest
from app.schemas.mock_interview import CreateMockInterviewRequest, SubmitMockAnswerRequest
from app.schemas.mock_interview import MockWireCommand
from app.services.chat_service import ChatService
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.screenshot_answer_service import ScreenshotAnswerService
from app.services.session_service import SessionService
from app.services.session_mode_guard import require_standard_session


def test_legacy_adapter_without_mode_keeps_ordinary_behavior():
    require_standard_session(SimpleNamespace(status="live"))


def test_legacy_create_rejects_mock_even_with_forged_request():
    with pytest.raises(ValidationError):
        CreateInterviewSessionRequest(userId="synthetic", title="合成面试", sessionMode="mock")
    with pytest.raises(DomainRequestError) as caught:
        SessionService.create_session(Mock(), user_id="synthetic", title="test", session_mode="mock")
    assert caught.value.error_code == "mock_dedicated_command_required"


def test_mock_commands_cannot_supply_owner_price_or_unbounded_answer():
    create = dict(idempotencyKey="synthetic", title="合成面试", expectedBillingClass="points")
    for extras in ({"userId": "other"}, {"entryPoints": 0}, {"refunded": True}):
        with pytest.raises(ValidationError):
            CreateMockInterviewRequest(**create, **extras)
    for answer in ("  ", "字" * 8001):
        with pytest.raises(ValidationError):
            SubmitMockAnswerRequest(version=0, questionId="q", submissionId="id", answer=answer)
    with pytest.raises(ValidationError):
        SubmitMockAnswerRequest(version=-1, questionId="q", submissionId="id", answer="合成回答")


def test_mock_socket_command_is_strict_and_uses_internal_field_names():
    command = MockWireCommand(action="submit", version=3, questionId="q", submissionId="s", answer="合成回答")
    assert command.model_dump(by_alias=False)["question_id"] == "q"
    for payload in ({"action": "listen", "version": 0},
                    {"action": "submit", "version": 0, "questionId": "q"},
                    {"action": "start", "version": 0, "userId": "other"},
                    {"action": "refund", "version": 0}):
        with pytest.raises(ValidationError): MockWireCommand.model_validate(payload)


def test_rollout_off_or_global_cannot_instantiate_service(monkeypatch):
    from app.modules import mock_interview
    for edition, flag in (("cn", False), ("global", True)):
        monkeypatch.setattr(mock_interview, "get_settings", lambda: SimpleNamespace(product_edition=edition, mock_interview_enabled=flag, global_mock_interview_enabled=False))
        with pytest.raises(DomainRequestError) as caught:
            mock_interview.require_mock_runtime()
        assert caught.value.error_code == "mock_not_enabled"


@pytest.mark.parametrize("method,kwargs,is_generator", [
    (SessionService.start_session, {}, False),
    (SessionService.restart_session, {}, False),
    (SessionService.delete_session, {}, False),
    (SessionService.continue_session, {}, False),
    (SessionService.update_interview_language, {"interview_language": "zh-CN"}, False),
    (SessionService.update_interview_audio_mode, {"interview_audio_mode": "computer"}, False),
    (SessionService.update_interview_programming, {"programming_required": True, "programming_language": "python"}, False),
    (SessionService.update_auto_answer, {"enabled": True}, False),
    (SessionService.confirm_materials, {"resume_document_id": None, "job_description_document_id": None, "knowledge_document_ids": []}, False),
    (RealtimeSpeechService.start_live_session, {}, False),
    (RealtimeSpeechService.control_capture, {"action": "resume"}, False),
    (RealtimeSpeechService.create_publisher, {"source_kind": "microphone", "client_name": "synthetic"}, False),
    (ChatService.answer_question, {"question": "合成问题", "stream": False}, False),
    (ChatService.stream_answer_question, {"question": "合成问题"}, True),
    (ScreenshotAnswerService._assert_session_uploadable, {}, False),
    (ScreenshotAnswerService.answer_screenshots, {"image_ids": [], "instruction": "合成", "stream": False}, False),
    (ScreenshotAnswerService.create_remote_capture_request, {"device_id": "synthetic", "manual_code": "123456", "instruction": "合成"}, False),
])
def test_old_commands_fail_before_any_side_effect(method, kwargs, is_generator):
    session = SimpleNamespace(session_mode="mock", status="live")
    obj = Mock()
    obj.get_session.return_value = session
    obj.session_service.get_session.return_value = session
    with pytest.raises(DomainRequestError) as caught:
        result = method(obj, user_id="synthetic", session_id="mock-synthetic", **kwargs)
        if is_generator:
            next(result)
    assert caught.value.error_code == "mock_dedicated_command_required"
    obj.billing_service.assert_not_called()
    obj._reserve_answer_usage.assert_not_called()
    obj._reserve_realtime_minute.assert_not_called()
    obj.repository.save_session.assert_not_called()
    obj.repository.save_task.assert_not_called()
