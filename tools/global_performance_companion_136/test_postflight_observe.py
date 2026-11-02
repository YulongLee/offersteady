"""Synthetic privacy and command-boundary regressions; no Docker or network."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def observer():
    path = Path(__file__).with_name('postflight_observe.py')
    spec = importlib.util.spec_from_file_location('test_postflight_observer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_logs_are_only_aggregate_counts(observer):
    private = b'phone=18200000000 resume=private_resume_token credential=never_export'
    logs = b'ERROR: ' + private + b'\nTraceback (most recent call last):\n'
    logs += b'127.0.0.1 - "POST /api/user/private_session HTTP/1.1" 503 Service Unavailable\n'
    logs += b'{"level":"CRITICAL","message":"' + private + b'","statusCode":500}\n'
    result = observer.log_counts(logs)
    assert result == {'rows': 4, 'tailLimitReached': False, 'errorLines': 2, 'tracebacks': 1, 'http5xx': 2}
    assert all(type(v) in (int, bool) for v in result.values())
    serialized = json.dumps(result)
    for secret in ('18200000000', 'private_resume_token', 'never_export', 'private_session'):
        assert secret not in serialized


def test_tail_limit_is_explicit(observer):
    assert observer.log_counts(b'ordinary\n' * 4000)['tailLimitReached'] is True
    assert observer.log_counts(b'ordinary\n' * 3999)['tailLimitReached'] is False


@pytest.mark.parametrize('command', [
    ['docker', 'start', 'protected'], ['docker', 'stop', 'protected'],
    ['docker', 'rm', 'protected'], ['docker', 'restart', 'protected'],
    ['docker', 'run', 'image'], ['docker', 'compose', 'up'],
    ['ssh', 'server'], ['sh', '-c', 'echo private'],
])
def test_mutation_commands_rejected_before_execution(observer, monkeypatch, command):
    monkeypatch.setattr(observer.subprocess, 'run', lambda *a, **k: pytest.fail('must reject before execution'))
    with pytest.raises(observer.ObservationError):
        observer.run_readonly(command)


def test_failed_command_never_creates_private_diagnostic(observer, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(observer.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        returncode=1, stdout=b'private_resume', stderr=b'credential=never_export'))
    with pytest.raises(observer.ObservationError, match='^readonly_observation_command_failed$'):
        observer.run_readonly(['docker', 'inspect', 'synthetic'])
    assert list(tmp_path.iterdir()) == []


def test_cli_redacts_every_exception_and_never_writes(observer, monkeypatch, tmp_path, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError('phone18200000000 secret=never_export /private/file')
    monkeypatch.setattr(observer, 'observe', fail)
    monkeypatch.chdir(tmp_path)
    assert observer.main(['--worker-inventory', '/not/read', '--since-ms', '1']) == 1
    assert json.loads(capsys.readouterr().out) == {
        'passed': False, 'reason': 'postflight_observation_failed',
        'rawLogsExported': False, 'configurationExported': False}
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('since,now', [(0, 3600001), (1001, 1000), (-1, 3600000)])
def test_invalid_window_rejected_before_any_file_or_command(observer, since, now):
    with pytest.raises(observer.ObservationError, match='observation_window_invalid'):
        observer.observe(Path('/nonexistent'), Path('/nonexistent'), since, now_ms=now)


def test_permission_guard_rejects_public_file_as_private(observer, tmp_path):
    path = tmp_path / 'public.json'
    path.write_text('{}')
    path.chmod(0o600)
    with pytest.raises(observer.ObservationError, match='release_file_permissions_changed'):
        observer.checked_file(path, 0o644)


def test_importing_tool_does_not_import_release_entrypoint(observer):
    import ast
    source = Path(observer.__file__).read_text()
    module = ast.parse(source)
    imports = [n.module or '' for n in ast.walk(module) if isinstance(n, ast.ImportFrom)]
    assert all('release_global_performance' not in name for name in imports)
    assert 'spec_from_file_location(name, path)' in source
