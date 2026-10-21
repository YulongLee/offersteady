"""Read-only candidate-image probe. Baseline settings stay in the container.

Run with --network none, original private environment, and only approved model
overrides. No app factory, lifespan, repository or actual provider is invoked.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
from pathlib import Path
import socket
import sys
from types import SimpleNamespace


TARGET = 'deepseek-v4.1-flash-1017'
MODEL_KEYS = {
    'backend': ('chat_qwen_model', 'chat_quick_model', 'chat_detail_model', 'screenshot_vision_model'),
    'material-worker': ('chat_qwen_model',),
}


def inspect_candidate(role: str, baseline_path: Path) -> dict:
    checks = []
    result = dict(passed=False, role=role, settingsDeltaKeys=[], checks=checks,
                  providerCalls=0, databaseWrites=0, workersStarted=0, lifespanStarted=False)
    network_attempts = []
    database_attempts = []

    def no_network(*args, **kwargs):
        network_attempts.append(True)
        raise RuntimeError('candidate_probe_network_forbidden')

    def no_database(*args, **kwargs):
        database_attempts.append(True)
        raise RuntimeError('candidate_probe_database_forbidden')

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    import psycopg
    original_pg_connect = psycopg.connect
    psycopg.connect = no_database
    try:
        from app.core.config import Settings
        from app.services import document_processing

        assert 'app.deps' not in sys.modules and 'app.main' not in sys.modules
        checks.append('no_application_factory_or_lifespan_import')
        baseline = json.loads(baseline_path.read_text())
        assert isinstance(baseline, dict)
        settings = Settings(_env_file=None)
        actual = settings.model_dump(mode='json')
        keys = MODEL_KEYS[role]
        assert set(actual) == set(baseline) and all(key in baseline for key in keys)
        expected = dict(baseline)
        expected.update(dict.fromkeys(keys, TARGET))
        assert actual == expected
        result['settingsDeltaKeys'] = sorted(key for key in actual if actual[key] != baseline[key])
        assert set(result['settingsDeltaKeys']) <= set(keys)
        if role == 'backend':
            assert settings.product_edition == 'global'
        checks.extend(['exact_approved_model_settings', 'all_other_settings_preserved'])

        original_httpx = document_processing.httpx
        source = 'SYNTHETIC: Python and PostgreSQL project. No performance measurements are available.'
        generated = 'Synthetic project uses Python and PostgreSQL; no measurements are available.'
        observations = []
        budgets = []
        for kind in ('resume', 'job_description'):
            for outcome in ('success', 'timeout', 'provider_error', 'empty'):
                def handle(request):
                    payload = json.loads(request.content)
                    assert payload['model'] == TARGET
                    assert payload['enable_thinking'] is False and payload['stream'] is False
                    assert payload['temperature'] == 0.1
                    observations.append((kind, outcome))
                    if outcome == 'timeout':
                        raise original_httpx.ReadTimeout('synthetic timeout', request=request)
                    if outcome == 'provider_error':
                        return original_httpx.Response(503)
                    return original_httpx.Response(200, json={'choices': [{'finish_reason': 'stop',
                        'message': {'content': generated if outcome == 'success' else ''}}]})

                def mock_client(*args, **kwargs):
                    budgets.append(kwargs['timeout'])
                    return original_httpx.Client(*args, transport=original_httpx.MockTransport(handle), **kwargs)

                isolated_httpx = SimpleNamespace(**vars(original_httpx))
                isolated_httpx.Client = mock_client
                document_processing.httpx = isolated_httpx
                try:
                    service = document_processing.DocumentProcessingService.__new__(
                        document_processing.DocumentProcessingService)
                    service.settings = settings
                    service.logger = logging.Logger('offline-model-release-probe', level=logging.CRITICAL + 1)
                    document = SimpleNamespace(document_id='synthetic-release-probe', document_kind=kind)
                    summary = service._build_interview_summary(document=document, markdown=source)
                    if outcome == 'success':
                        assert summary and summary.endswith(generated)
                    else:
                        assert summary == service._extractive_interview_summary(document=document, clean_text=source)
                finally:
                    document_processing.httpx = original_httpx
        assert len(observations) == len(budgets) == 8
        assert all((budget.connect, budget.read, budget.write, budget.pool) == (2.0, 8.0, 4.0, 2.0)
                   for budget in budgets)
        checks.extend(['summary_non_thinking_payload', 'summary_existing_eight_second_budget',
                       'summary_success_both_document_kinds', 'summary_existing_failure_fallback'])
        assert not network_attempts and not database_attempts
        assert 'app.deps' not in sys.modules and 'app.main' not in sys.modules
        checks.extend(['no_provider_network', 'no_database_access', 'no_worker_or_lifespan_started'])
        result['passed'] = True
        return result
    finally:
        psycopg.connect = original_pg_connect
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', required=True, choices=tuple(MODEL_KEYS))
    parser.add_argument('--baseline-settings', type=Path, required=True)
    args = parser.parse_args()
    output, errors = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = inspect_candidate(args.role, args.baseline_settings)
        if output.getvalue() or errors.getvalue():
            result['passed'] = False
            result['checks'].append('unexpected_output_refused')
    except Exception:
        result = dict(passed=False, role=args.role, settingsDeltaKeys=[], checks=['candidate_probe_failed'],
                      providerCalls=0, databaseWrites=0, workersStarted=0, lifespanStarted=False)
    print(json.dumps(result, allow_nan=False))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
