"""Isolated staging/upload orchestration; executor is synthetic and never connects."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('stage200', Path(__file__).with_name('stage_upload_cn_companion_200.py'))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)


@pytest.fixture
def payloads(monkeypatch, tmp_path):
    rows = []
    for i in range(3):
        content = f'synthetic-{i}'.encode(); p = tmp_path / f'{i}.dmg'; p.write_bytes(content)
        row = {'fileName': p.name, 'fileSizeBytes':len(content), 'sha256':hashlib.sha256(content).hexdigest(),
               'platform':'macos','architecture':str(i),'objectKey':f'test/{i}'}
        rows.append((row, p))
    monkeypatch.setattr(S, 'frozen_inputs', lambda: (rows, b'synthetic uploader'))
    return rows


def test_serial_staging_and_upload_with_frozen_bytes(payloads):
    actions=[]
    def executor(args, *, data=None, **kwargs):
        if args[0]=='python3': actions.append('ancestors'); return b'{"ok":true,"checkedAncestors":2}'
        code=args[9]
        if code == S.REMOTE_CAPACITY: actions.append('capacity'); return b'{"ok":true}'
        if code == S.REMOTE_MKDIR: actions.append('mkdir'); return b''
        if code == S.REMOTE_STAGE:
            actions.append('stage'); meta=json.loads(args[-1]); assert hashlib.sha256(data).hexdigest()==meta['sha256']
            return json.dumps({'staged':True,'size':len(data),'sha256':meta['sha256']}).encode()
        assert code == 'synthetic uploader'; actions.append('upload'); row=payloads[actions.count('upload')-1][0]
        return json.dumps({'objectReadbackVerified':True, **{k:row[k] for k in ('sha256','fileSizeBytes','objectKey')}}).encode()
    result=S.run(executor)
    assert len(result)==3
    assert actions==['ancestors','capacity','mkdir']+['ancestors','capacity','stage','upload']*3


def test_capacity_failure_performs_no_staging(payloads):
    actions=[]
    def executor(args, **kwargs):
        if args[0]=='python3': return b'{"ok":true}'
        actions.append(args[9]); return b'{"ok":false}'
    with pytest.raises(S.GuardError, match='capacity_unavailable'): S.run(executor)
    assert actions==[S.REMOTE_CAPACITY]


def test_ambiguous_upload_never_retries_or_advances(payloads):
    actions=[]
    def executor(args, *, data=None, **kwargs):
        if args[0]=='python3': return b'{"ok":true}'
        code=args[9]; actions.append(code)
        if code==S.REMOTE_CAPACITY: return b'{"ok":true}'
        if code==S.REMOTE_MKDIR: return b''
        if code==S.REMOTE_STAGE:
            meta=json.loads(args[-1]); return json.dumps({'staged':True,'size':len(data),'sha256':meta['sha256']}).encode()
        raise S.GuardError('remote_operation_failed_or_unknown')
    with pytest.raises(S.GuardError): S.run(executor)
    assert actions.count('synthetic uploader')==1 and actions.count(S.REMOTE_STAGE)==1


def test_ancestor_gate_failure_stops_before_capacity_or_staging(payloads):
    calls=[]
    def executor(args, **kwargs): calls.append(args); return b'{"ok":false}'
    with pytest.raises(S.GuardError, match='ancestor_capacity_unavailable'): S.run(executor)
    assert len(calls)==1 and calls[0][0]=='python3'


@pytest.mark.parametrize('maximum, current, allowed', [('max', '0', True), ('2147483648','1073741824',False), ('4294967296','1073741824',True)])
def test_actual_host_ancestor_program_obeys_parent_limit(monkeypatch, capsys, maximum, current, allowed):
    from types import SimpleNamespace
    values={'/proc/123/cgroup':'0::/parent/child\n', '/sys/fs/cgroup/parent/child/memory.max':'max',
            '/sys/fs/cgroup/parent/memory.max':maximum, '/sys/fs/cgroup/parent/memory.current':current}
    monkeypatch.setattr(Path, 'read_text', lambda self: values[str(self)])
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=f'{S.CONTAINER} 123 true\n'))
    monkeypatch.setattr(sys, 'argv', ['-c', S.CONTAINER])
    if allowed:
        exec(S.HOST_ANCESTORS, {})
        assert json.loads(capsys.readouterr().out)=={'ok':True,'checkedAncestors':2}
    else:
        with pytest.raises(SystemExit): exec(S.HOST_ANCESTORS, {})


def test_remote_stage_refuses_overwrite_traversal_and_mismatch(tmp_path):
    data=b'synthetic'; meta={'sha256':hashlib.sha256(data).hexdigest(),'fileSizeBytes':len(data)}
    def stage(name, body=data):
        return subprocess.run([sys.executable,'-B','-c',S.REMOTE_STAGE,str(tmp_path),name,json.dumps(meta)],input=body,capture_output=True)
    assert stage('../escape').returncode != 0
    assert stage('safe').returncode == 0
    assert stage('safe').returncode != 0
    assert (tmp_path/'safe').read_bytes()==data
    assert stage('wrong',b'corrupted').returncode != 0
    assert not (tmp_path/'wrong.json').exists()
    (tmp_path/'link').symlink_to(tmp_path/'safe')
    assert stage('link').returncode != 0
    assert (tmp_path/'safe').read_bytes()==data


def test_remote_stage_refuses_symlink_directory(tmp_path):
    target=tmp_path/'actual'; target.mkdir()
    link=tmp_path/'redirect'; link.symlink_to(target, target_is_directory=True)
    data=b'synthetic'; meta={'sha256':hashlib.sha256(data).hexdigest(),'fileSizeBytes':len(data)}
    result=subprocess.run([sys.executable,'-B','-c',S.REMOTE_STAGE,str(link),'safe',json.dumps(meta)],input=data,capture_output=True)
    assert result.returncode != 0
    assert list(target.iterdir()) == []
