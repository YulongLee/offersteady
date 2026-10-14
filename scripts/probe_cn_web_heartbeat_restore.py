"""Synthetic heartbeat checks inside an immutable, network-isolated CN image.

No application startup, provider calls, production repositories or user data.
Static API/entitlement evidence supplements (but does not replace) the release
tool's proof that every unrelated AST node and file equals the running baseline.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import fields, replace
import hashlib
import json
from pathlib import Path
import sys
import threading
from unittest.mock import Mock, patch


NOW = 1_800_000_000_000


def _require(value, message):
    if not value:
        raise AssertionError(message)


def _node(tree, name, class_name=None):
    scope = tree.body
    if class_name:
        scope = next(item for item in scope if isinstance(item, ast.ClassDef) and item.name == class_name).body
    return next(item for item in scope if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name)


def static_evidence(backend_path):
    """Inspect API declarations only; never import/start routes or billing."""
    app = Path(backend_path) / "app"
    paths = ("api/v1.py", "modules/mock_interview.py", "services/realtime_speech_service.py", "services/billing_service.py")
    sources = {path: (app / path).read_text() for path in paths}
    trees = {path: ast.parse(source) for path, source in sources.items()}
    mock_router_present = any(
        isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
        and item.func.attr == "include_router" and item.args
        and ast.dump(item.args[0]) == ast.dump(ast.parse("mock_interview.router", mode="eval").body)
        for item in ast.walk(trees["api/v1.py"])
    )
    _require(mock_router_present, "mock interview API router omitted")
    capability = _node(trees["modules/mock_interview.py"], "capabilities")
    _require(any(isinstance(item, ast.Constant) and item.value == "enabled" for item in ast.walk(capability)),
             "mock capabilities declaration omitted")
    _require(any(isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == "enabled"
                 for item in ast.walk(capability)), "mock capabilities rollout check omitted")
    start_live = _node(trees["services/realtime_speech_service.py"], "start_live_session", "RealtimeSpeechService")
    reservations = [item for item in ast.walk(start_live)
                    if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
                    and item.func.attr == "reserve_usage"
                    and any(keyword.arg == "usage_kind" and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value == "written_exam_entry" for keyword in item.keywords)]
    _require(len(reservations) == 1, "written exam entitlement reservation omitted or duplicated")
    wallet_keywords = [keyword.value for keyword in reservations[0].keywords if keyword.arg == "wallet_only"]
    reserve_usage = _node(trees["services/billing_service.py"], "reserve_usage", "BillingService")
    wallet_defaults = [default for argument, default in zip(reserve_usage.args.kwonlyargs, reserve_usage.args.kw_defaults)
                       if argument.arg == "wallet_only"]
    # An omitted argument is inclusive only when its actual implementation's
    # keyword-only default is False; explicit False has the same behavior.
    wallet_values = wallet_keywords if wallet_keywords else wallet_defaults
    _require(len(wallet_values) == 1 and isinstance(wallet_values[0], ast.Constant)
             and wallet_values[0].value is False, "written exam inclusive time pass rule omitted")
    return {
        "kind": "source-declarations-only",
        "mockApiRouterIncluded": True,
        "mockCapabilitiesDeclared": True,
        "writtenExamTimePassInclusive": True,
        "fileSha256": {path: hashlib.sha256(source.encode()).hexdigest() for path, source in sources.items()},
        "protectedNodeAstSha256": {
            "mock_capabilities": hashlib.sha256(ast.dump(capability, include_attributes=False).encode()).hexdigest(),
            "start_live_session": hashlib.sha256(ast.dump(start_live, include_attributes=False).encode()).hexdigest(),
            "reserve_usage": hashlib.sha256(ast.dump(reserve_usage, include_attributes=False).encode()).hexdigest(),
        },
    }


def run_probe(backend_path, *, candidate_image=None, static_checks=True):
    backend_path = Path(backend_path).resolve()
    sys.path.insert(0, str(backend_path))
    from app.core.config import Settings
    from app.core.errors import DomainRequestError
    from app.ports.interview_session import SessionBoundDocument, SessionHeartbeatState
    from app.services.interview_session_repository import InMemoryInterviewSessionRepository
    from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
    from app.services.realtime_speech_service import RealtimeSpeechService
    from app.services.session_service import SessionService
    import app.services.realtime_speech_service as realtime_module
    import app.services.session_service as session_module

    # Ensure the supplied source root is what Python actually executes.
    source = backend_path / "app/services/realtime_speech_service.py"
    _require(Path(realtime_module.__file__).resolve() == source, "imported source does not match candidate root")
    _require(Path(session_module.__file__).resolve() == backend_path / "app/services/session_service.py",
             "imported session source does not match candidate root")
    checks = []

    def done(name):
        checks.append({"name": name, "passed": True})

    def fixture(*, status="live", last_activity=NOW, documents=25):
        settings = Settings(_env_file=None, database_url=None, redis_url=None,
                            interview_idle_warning_seconds=60, interview_idle_timeout_seconds=120,
                            realtime_web_heartbeat_ttl_seconds=45)
        repository = InMemoryInterviewSessionRepository()
        materials = Mock()
        materials.get_by_id.return_value = None
        sessions = SessionService(settings=settings, repository=repository, document_repository=materials)
        created = sessions.create_session(user_id="synthetic-heartbeat-owner", title="Synthetic heartbeat restoration probe")
        record = replace(created, status=status, last_activity_at_ms=last_activity,
                         started_at_ms=None if status == "preparing" else NOW - 10_000,
                         material_binding=replace(created.material_binding, bound_documents=[
                             SessionBoundDocument(document_id=f"synthetic-material-{index}", document_kind="knowledge",
                                                  display_name=f"Synthetic material {index}", status="ready")
                             for index in range(documents)]))
        repository.save_session(record)
        realtime = object.__new__(RealtimeSpeechService)
        realtime.settings, realtime.session_service = settings, sessions
        realtime.repository = InMemoryRealtimeSpeechRepository(state_file=None)
        realtime._session_activity_lock = threading.Lock()
        realtime._session_last_activity_ms, realtime._session_owners = {}, {}
        realtime.terminate_session_for_admin = Mock()
        realtime.billing_service = Mock()
        return realtime, sessions, repository, materials, record

    def beat(realtime, record, *, user=None, page="live", instance="synthetic-page", binding=None):
        return realtime.record_web_session_heartbeat(user_id=user or record.owner_user_id,
            session_id=record.session_id, binding_id=binding, page=page, page_instance_id=instance)

    def expect_error(action, status, code=None):
        try:
            action()
        except DomainRequestError as error:
            _require(error.status_code == status, f"expected HTTP {status}")
            if code:
                _require(error.error_code == code, "lifecycle error code changed")
        else:
            raise AssertionError(f"expected HTTP {status}")

    with patch.object(session_module, "_now_ms", return_value=NOW), patch.object(realtime_module, "_now_ms", return_value=NOW):
        for status in ("preparing", "live"):
            realtime, _, repository, materials, record = fixture(status=status)
            projection = Mock(wraps=repository.get_heartbeat_state)
            repository.get_heartbeat_state = projection
            repository.get_session = Mock(side_effect=AssertionError("full session read on normal heartbeat"))
            for name in ("save_session", "save_usage_record", "touch_activity", "append_context_entry"):
                setattr(repository, name, Mock(side_effect=AssertionError("session or billing write on normal heartbeat")))
            result = beat(realtime, record, binding="synthetic-binding")
            projection.assert_called_once_with(record.session_id)
            materials.get_by_id.assert_not_called()
            _require(repository.sessions[record.session_id] == record and not repository.usage_records,
                     "normal heartbeat mutated session or billing state")
            _require(not realtime.billing_service.mock_calls, "normal heartbeat invoked billing")
            _require(result.session_id == record.session_id and result.owner_user_id == record.owner_user_id
                     and result.binding_id == "synthetic-binding" and result.seen_at_ms == NOW
                     and result.lease_expires_at_ms == NOW + 45_000, "heartbeat response changed")
            done(f"{status}: one projection, no full/material read, no session/billing write")

        _, _, repository, _, record = fixture()
        state = repository.get_heartbeat_state(record.session_id)
        _require(isinstance(state, SessionHeartbeatState), "heartbeat projection type changed")
        _require({field.name for field in fields(state)} == {
            "session_id", "owner_user_id", "status", "started_at_ms", "last_activity_at_ms"},
            "heartbeat projection contains heavy fields")
        done("projection contains exactly five lifecycle fields")

        for status in ("preparing", "live", "ended"):
            _, sessions, _, _, record = fixture(status=status, documents=0)
            for offset, expected in ((0, "active"), (59_999, "active"), (60_000, "warning"),
                                     (119_999, "warning"), (120_000, "expired")):
                actual = sessions.heartbeat_idle_status(user_id=record.owner_user_id, session_id=record.session_id, at_ms=NOW + offset)
                legacy = sessions.idle_status(user_id=record.owner_user_id, session_id=record.session_id, at_ms=NOW + offset)
                _require(actual == legacy, "idle projection changes legacy time calculation")
                _require(actual["state"] == ("ended" if status == "ended" else "active" if status == "preparing" else expected),
                         "idle warning or expiry boundary changed")
            done(f"{status}: legacy idle boundaries retained")

        realtime, _, _, _, record = fixture(last_activity=NOW - 60_000)
        _require(beat(realtime, record).lease_expires_at_ms == NOW + 45_000, "warning heartbeat did not renew lease")
        realtime.terminate_session_for_admin.assert_not_called()
        done("idle warning allows the original heartbeat lease")

        for missing, user, status in ((False, "synthetic-other-owner", 403), (True, "synthetic-heartbeat-owner", 404)):
            realtime, _, repository, materials, record = fixture()
            if missing:
                repository.sessions.clear()
            expect_error(lambda: beat(realtime, record, user=user), status)
            _require(realtime._session_owners == realtime._session_last_activity_ms == {}, "denied heartbeat touched activity")
            _require(not realtime.repository.web_session_heartbeats, "denied heartbeat saved lease")
            materials.get_by_id.assert_not_called()
            done(f"HTTP {status}: no activity or lease side effects")

        realtime, _, _, _, record = fixture(status="ended")
        expect_error(lambda: beat(realtime, record), 409, "realtime_session_ended")
        _require(not realtime.repository.web_session_heartbeats, "ended heartbeat saved lease")
        realtime.terminate_session_for_admin.assert_not_called()
        done("HTTP 409: ended session is denied")

        realtime, _, repository, _, record = fixture()
        first = beat(realtime, record)
        repository.save_session(replace(record, status="ended"))
        expect_error(lambda: beat(realtime, record), 409, "realtime_session_ended")
        _require(realtime.repository.get_active_live_web_session(user_id=record.owner_user_id) == first,
                 "ended next heartbeat renewed lease")
        done("authoritative end seen on next heartbeat without cache")

        for cleanup_fails in (False, True):
            realtime, _, _, _, record = fixture(last_activity=NOW - 120_000)
            if cleanup_fails:
                realtime.terminate_session_for_admin.side_effect = RuntimeError("synthetic cleanup fault")
                try:
                    beat(realtime, record)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("cleanup failure became successful heartbeat")
            else:
                expect_error(lambda: beat(realtime, record), 409, "realtime_session_ended")
            realtime.terminate_session_for_admin.assert_called_once_with(
                user_id=record.owner_user_id, session_id=record.session_id, reason="idle-timeout")
            _require(not realtime.repository.web_session_heartbeats, "expired heartbeat saved lease")
            done("expiry cleanup failure propagates" if cleanup_fails else "expiry invokes original cleanup then HTTP 409")

        realtime, _, _, _, record = fixture()
        first = beat(realtime, record, instance="  synthetic-page-a  ")
        renewed = beat(realtime, record, instance="synthetic-page-a")
        _require(first.page_instance_id == "synthetic-page-a" and first.lease_generation == renewed.lease_generation,
                 "same-page lease renewal generation changed")
        done("live atomic claim and same-page lease renewal preserved")
        preparation = beat(realtime, record, page="preparation", instance=None)
        _require(preparation == renewed, "preparation overwrote existing live lease")
        done("preparation shares valid live lease")
        replacement = beat(realtime, record, instance="synthetic-page-b")
        _require(replacement.page_instance_id == "synthetic-page-b" and replacement.lease_generation >= renewed.lease_generation,
                 "page takeover generation regressed")
        done("page takeover uses existing claim semantics")

        realtime, sessions, _, materials, record = fixture(documents=1)
        beat(realtime, record)
        materials.get_by_id.assert_not_called()
        refreshed = sessions.get_session(user_id=record.owner_user_id, session_id=record.session_id)
        materials.get_by_id.assert_called_once_with("synthetic-material-0")
        _require(not refreshed.material_binding.bound_documents[0].active, "non-heartbeat path skipped changed material")
        done("ordinary full read retains changed-material refresh")

    evidence = static_evidence(backend_path) if static_checks else {"kind": "disabled-for-local-unit-tests"}
    if static_checks:
        done("static mock API and inclusive written exam entitlement declarations retained")
    return {"passed": True, "checks": len(checks), "checkResults": checks, "syntheticOnly": True,
            "networkRequired": False, "candidateImage": candidate_image,
            "sourceAfterSha256": hashlib.sha256(source.read_bytes()).hexdigest(), "staticEvidence": evidence}


def main(argv=None):
    default = Path("/app/apps/backend")
    if not default.is_dir():
        default = Path(__file__).resolve().parents[1] / "apps/backend"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-path", type=Path, default=default)
    parser.add_argument("--candidate-image", help="Immutable image digest supplied by the release runner")
    args = parser.parse_args(argv)
    try:
        result = run_probe(args.backend_path, candidate_image=args.candidate_image)
    except Exception as error:
        # Do not print arbitrary exception text: dependencies may contain private
        # configuration. Check failures use safe, synthetic assertion messages.
        result = {"passed": False, "checks": 0, "syntheticOnly": True, "networkRequired": False,
                  "candidateImage": args.candidate_image, "errorClass": type(error).__name__}
        if isinstance(error, AssertionError):
            result["failure"] = str(error)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
