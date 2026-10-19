"""Full application schema and real formatting probe without app lifespan/I/O."""
from pathlib import Path
from io import BytesIO
import hashlib
import inspect
import json
import os
import socket
import subprocess
import sys
import threading
import traceback
from zipfile import ZipFile

import psycopg
import redis


def main():
    expected = json.loads(Path('/verify/expectations.json').read_text())
    counters = {'network': 0, 'database': 0, 'fileWrites': 0, 'threadStarts': 0, 'subprocesses': 0, 'dependenciesResolved': 0, 'lifespan': 0}

    def reject(kind):
        def blocked(*args, **kwargs):
            counters[kind] += 1
            raise RuntimeError('offline_probe_side_effect_rejected')
        return blocked

    psycopg.connect = reject('database')
    psycopg.Connection.connect = reject('database')
    psycopg.AsyncConnection.connect = reject('database')
    redis.Redis.execute_command = reject('database')
    threading.Thread.start = reject('threadStarts')
    subprocess.Popen = reject('subprocesses')
    socket.create_connection = reject('network')

    def audit(event, args):
        if event.startswith('socket.'):
            reject('network')()
        if event == 'open':
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else 0
            if isinstance(mode, str) and any(c in mode for c in 'wax+') or isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                reject('fileWrites')()
        if event in ('os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.chmod', 'os.chown', 'os.truncate', 'os.link', 'os.symlink', 'os.utime', 'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn'):
            reject('fileWrites' if event.startswith('os.') else 'subprocesses')()
    sys.addaudithook(audit)

    root = Path('/app')
    sys.path.insert(0, str(root / 'apps/backend'))
    actual = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for d in ('apps/backend/app', 'apps/backend/migrations', 'ai/prompts')
              for p in (root / d).rglob('*') if p.is_file() and '__pycache__' not in p.parts
              and p.suffix != '.pyc' and p.name != '.desktop-release-manifest.lock'}
    actual['apps/backend/pyproject.toml'] = hashlib.sha256((root / 'apps/backend/pyproject.toml').read_bytes()).hexdigest()
    assert actual == expected['inventory'], 'full_source_inventory_mismatch'
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    assert settings.product_edition == 'global' and settings.environment == 'production'
    assert settings.global_resume_optimizer_enabled is True
    data = {k: getattr(settings, k) for k in expected['configFields']}
    assert hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest() == expected['configBeforeSha']
    from app import deps
    # Preserve signatures so FastAPI's schemas do not change, while making
    # accidental service construction during module import fail closed.
    for name in ('document_service', 'document_read_service', 'document_processing_service', 'document_parser_service', 'chat_service', 'realtime_speech_service', 'screenshot_answer_service', 'session_service', 'resume_optimizer_repository', 'resume_optimizer_service', 'authentication_service', 'billing_service', 'usage_billing_service', 'global_commerce_service', 'global_checkout_service', 'admin_service', 'llm_gateway_port', 'storage_port', 'document_repository', 'processing_task_repository', 'embedding_adapter', 'database_runtime'):
        factory = getattr(deps, name, None)
        if factory is not None and callable(factory):
            blocked = reject('dependenciesResolved')
            blocked.__signature__ = inspect.signature(factory, eval_str=True)
            setattr(deps, name, blocked)
    from app.main import app
    app.router.lifespan_context = reject('lifespan')
    schema = app.openapi()
    assert schema == expected['openapiAfter'], 'full_candidate_schema_mismatch'
    for path, methods in expected['openapiBefore']['paths'].items():
        assert schema['paths'][path] == methods, 'old_route_behavior_schema_changed'
    for name, spec in expected['openapiBefore']['components']['schemas'].items():
        assert schema['components']['schemas'][name] == spec, 'old_schema_component_changed'
    added = set(schema['paths']) - set(expected['openapiBefore']['paths'])
    assert added and all(p.startswith('/api/v1/resume-optimizer') for p in added)
    from app.services.resume_optimizer_export import render_resume_export
    import reportlab
    assert reportlab.Version == '4.4.9'
    source = '# Synthetic Résumé 王小明 山田 한글\n\n## Experience\n- Improved processing by 28% in 2025.\n\ncontact@example.test\nFINAL CONTENT MARKER'
    docx, mime, name = render_resume_export(source, 'docx')
    assert mime.endswith('wordprocessingml.document') and name.endswith('.docx')
    with ZipFile(BytesIO(docx)) as archive:
        assert '王小明'.encode() in archive.read('word/document.xml')
        assert b'FINAL CONTENT MARKER' in archive.read('word/document.xml')
    pdf, mime, name = render_resume_export(source, 'pdf')
    assert pdf.startswith(b'%PDF-') and len(pdf) > 10000 and mime == 'application/pdf'
    assert all(v == 0 for v in counters.values()), 'side_effect_attempted'
    return {'passed': True, 'applicationAndPromptFiles': len(actual), 'httpPaths': len(schema['paths']), 'addedPaths': sorted(added), 'schemaSha256': hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'realDocxAndPdf': True, 'sideEffects': counters, 'lifespanEntered': counters['lifespan'] != 0}


if __name__ == '__main__':
    try:
        result = main()
        print(json.dumps(result))
    except BaseException as exc:
        print(json.dumps({'passed': False, 'errorType': type(exc).__name__, 'locations': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name} for f in traceback.extract_tb(exc.__traceback__)[-8:]]}))
        raise SystemExit(1) from None
