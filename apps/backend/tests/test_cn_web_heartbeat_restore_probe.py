"""Synthetic probe regressions; no Docker, network, providers or product data."""
import importlib.util
import json
from pathlib import Path

import pytest

from app.services.realtime_speech_service import RealtimeSpeechService


@pytest.fixture
def probe():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("heartbeat_restore_probe", root / "scripts/probe_cn_web_heartbeat_restore.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def backend_path():
    import app.services.realtime_speech_service as module
    return Path(module.__file__).resolve().parents[2]


def test_synthetic_probe_exercises_lifecycle_reads_and_materials(probe):
    result = probe.run_probe(backend_path(), candidate_image="sha256:synthetic-unit-image", static_checks=False)
    assert result["passed"] and result["checks"] >= 17
    assert result["checks"] == len(result["checkResults"])
    assert result["syntheticOnly"] is True and result["networkRequired"] is False
    assert len(result["sourceAfterSha256"]) == 64
    assert result["candidateImage"] == "sha256:synthetic-unit-image"


def test_probe_rejects_regressed_full_session_read(probe, monkeypatch):
    original = RealtimeSpeechService.record_web_session_heartbeat

    def full_read_again(service, **kwargs):
        service.session_service.get_session(user_id=kwargs["user_id"], session_id=kwargs["session_id"])
        return original(service, **kwargs)

    monkeypatch.setattr(RealtimeSpeechService, "record_web_session_heartbeat", full_read_again)
    with pytest.raises(AssertionError, match="full session read"):
        probe.run_probe(backend_path(), static_checks=False)


def test_probe_rejects_session_or_billing_write(probe, monkeypatch):
    original = RealtimeSpeechService.record_web_session_heartbeat

    def writes_again(service, **kwargs):
        service.session_service.repository.touch_activity(
            user_id=kwargs["user_id"], session_id=kwargs["session_id"], activity_at_ms=probe.NOW)
        return original(service, **kwargs)

    monkeypatch.setattr(RealtimeSpeechService, "record_web_session_heartbeat", writes_again)
    with pytest.raises(AssertionError, match="session or billing write"):
        probe.run_probe(backend_path(), static_checks=False)


def test_probe_cannot_silently_import_another_source_root(probe, tmp_path):
    with pytest.raises(AssertionError, match="imported source does not match"):
        probe.run_probe(tmp_path, static_checks=False)


def test_probe_failure_is_json_and_nonzero_without_private_error_details(probe, monkeypatch, capsys):
    def failed(*args, **kwargs):
        raise RuntimeError("SYNTHETIC_PRIVATE_CONFIG_DO_NOT_PRINT")

    monkeypatch.setattr(probe, "run_probe", failed)
    assert probe.main(["--candidate-image", "sha256:synthetic-unit-image"]) == 1
    output = capsys.readouterr().out
    assert "SYNTHETIC_PRIVATE_CONFIG_DO_NOT_PRINT" not in output
    result = json.loads(output)
    assert result["passed"] is False and result["errorClass"] == "RuntimeError"


def write_static_fixture(tmp_path, *, include_mock=True, inclusive=True):
    app = tmp_path / "app"
    for directory in ("api", "modules", "services"):
        (app / directory).mkdir(parents=True, exist_ok=True)
    (app / "api/v1.py").write_text("api_router.include_router(mock_interview.router)\n" if include_mock else "api_router = None\n")
    (app / "modules/mock_interview.py").write_text("def capabilities(request):\n    return {'enabled': enabled()}\n")
    (app / "services/realtime_speech_service.py").write_text(
        "class RealtimeSpeechService:\n    def start_live_session(self):\n"
        f"        self.billing_service.reserve_usage(usage_kind='written_exam_entry', wallet_only={not inclusive})\n")
    (app / "services/billing_service.py").write_text("class BillingService:\n    def reserve_usage(self, *, wallet_only=False):\n        pass\n")


def test_static_evidence_has_mock_router_and_inclusive_written_exam_rule(probe, tmp_path):
    write_static_fixture(tmp_path)
    result = probe.static_evidence(tmp_path)
    assert result["kind"] == "source-declarations-only"
    assert result["mockApiRouterIncluded"] and result["writtenExamTimePassInclusive"]
    assert all(len(value) == 64 for value in result["fileSha256"].values())


def test_static_evidence_accepts_omitted_wallet_argument_only_with_inclusive_default(probe, tmp_path):
    write_static_fixture(tmp_path)
    realtime = tmp_path / "app/services/realtime_speech_service.py"
    realtime.write_text(realtime.read_text().replace(", wallet_only=False", ""))
    assert probe.static_evidence(tmp_path)["writtenExamTimePassInclusive"] is True
    billing = tmp_path / "app/services/billing_service.py"
    billing.write_text(billing.read_text().replace("wallet_only=False", "wallet_only=True"))
    with pytest.raises(AssertionError, match="inclusive time pass rule omitted"):
        probe.static_evidence(tmp_path)


@pytest.mark.parametrize("include_mock,inclusive,expected", [
    (False, True, "mock interview API router omitted"),
    (True, False, "inclusive time pass rule omitted"),
])
def test_static_evidence_rejects_previous_feature_regressions(probe, tmp_path, include_mock, inclusive, expected):
    write_static_fixture(tmp_path, include_mock=include_mock, inclusive=inclusive)
    with pytest.raises(AssertionError, match=expected):
        probe.static_evidence(tmp_path)
