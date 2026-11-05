"""Regression for the shipped 1.3.2 main-process heartbeat, not a new client."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.errors import DomainRequestError
from app.services.mock_interview_runtime import MockInterviewRuntime
from app.services.realtime_speech_service import RealtimeSpeechService


def readiness_runtime(capabilities):
    runtime = MockInterviewRuntime.__new__(MockInterviewRuntime)
    realtime = runtime.realtime = Mock()
    realtime.session_service.get_session.return_value = SimpleNamespace(session_mode="mock", status="preparing")
    device = SimpleNamespace(device_id="synthetic-device", generation=1, capabilities=capabilities)
    binding = SimpleNamespace(device_id=device.device_id, binding_generation=1, status="bound", manual_code="000000")
    realtime.repository.get_desktop_device_by_code.return_value = device
    realtime.get_desktop_binding.return_value = binding
    realtime._desktop_device_fresh.return_value = True
    realtime._permission_status.side_effect = RealtimeSpeechService._permission_status
    return runtime, device, binding


@pytest.mark.parametrize("permission", ["unknown", None, "granted"])
def test_shipped_unknown_or_missing_is_not_denied_and_never_rewrites_device(permission):
    caps = {"protocolVersion": "2.0", "appVersion": "1.3.2"}
    if permission is not None:
        caps["microphone"] = permission
    runtime, device, binding = readiness_runtime(caps.copy())
    assert runtime._device_readiness("synthetic-owner", "synthetic-session") == (binding, permission != "granted")
    assert runtime.validate_device("synthetic-owner", "synthetic-session") is binding
    assert device.capabilities == caps
    runtime.realtime.repository.save_desktop_device.assert_not_called()


@pytest.mark.parametrize("caps,code", [
    ({"protocolVersion": "2.0", "microphone": "denied"}, "mock_microphone_required"),
    ({"protocolVersion": "2.0", "microphone": "restricted"}, "mock_microphone_required"),
    ({"protocolVersion": "2.0", "microphone": "invalid"}, "mock_microphone_required"),
    ({"protocolVersion": "2.0", "mockInterviewProtocol": 1, "microphone": "unknown"}, "mock_microphone_required"),
    ({"protocolVersion": "1.0", "microphone": "unknown"}, "mock_desktop_incompatible"),
])
def test_explicit_denial_and_nonlegacy_unknown_still_block(caps, code):
    runtime, _, _ = readiness_runtime(caps)
    with pytest.raises(DomainRequestError) as caught:
        runtime.validate_device("synthetic-owner", "synthetic-session")
    assert caught.value.error_code == code


@pytest.mark.parametrize("failure", ["offline", "generation", "device", "unbound", "ended", "ordinary", "missing"])
def test_unknown_permission_does_not_bypass_binding_or_lifecycle(failure):
    runtime, device, binding = readiness_runtime({"protocolVersion": "2.0", "microphone": "unknown"})
    if failure == "offline": runtime.realtime._desktop_device_fresh.return_value = False
    if failure == "generation": binding.binding_generation += 1
    if failure == "device": binding.device_id = "other"
    if failure == "unbound": binding.status = "unbound"
    if failure == "ended": runtime.realtime.session_service.get_session.return_value.status = "ended"
    if failure == "ordinary": runtime.realtime.session_service.get_session.return_value.session_mode = "interview"
    if failure == "missing": runtime.realtime.repository.get_desktop_device_by_code.return_value = None
    with pytest.raises(DomainRequestError):
        runtime.validate_device("synthetic-owner", "synthetic-session")
