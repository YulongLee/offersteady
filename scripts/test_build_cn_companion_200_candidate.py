import importlib.util
import sys
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cn200_build', REPO/'scripts/build_cn_companion_200_candidate.py')
B=importlib.util.module_from_spec(spec);sys.modules[spec.name]=B;spec.loader.exec_module(B)
def make_context(root):
    root.mkdir()
    (root/'Dockerfile').write_text('FROM sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43\nCOPY overlay/ /app/\n')
    with tarfile.open(REPO/'releases/20261115.1/cn/backend-runtime.tar.gz', 'r:gz') as archive:
        for name in ('apps/backend/app/modules/web.py', 'apps/backend/app/desktop_release_manifest.json'):
            member=archive.extractfile(name)
            assert member is not None
            target=root/'overlay'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(member.read())
            target.chmod(0o644)
    return root

@pytest.fixture(autouse=True)
def reject_external_calls():
    with patch('subprocess.run',side_effect=AssertionError('unmocked process forbidden')):
        yield

def test_exact_context_and_reject_extra_or_symlink():
    with tempfile.TemporaryDirectory() as tmp:
        p=make_context(Path(tmp)/'ctx');B.validate_context(p)
        (p/'overlay/extra').write_text('bad')
        with pytest.raises(B.GuardError,match='context_inventory_invalid'): B.validate_context(p)
        (p/'overlay/extra').unlink();(p/'overlay/link').symlink_to('apps')
        with pytest.raises(B.GuardError,match='context_symlink_refused'): B.validate_context(p)

def test_tamper_and_hardlink_are_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        p=make_context(Path(tmp)/'ctx');t=p/'overlay/apps/backend/app/modules/web.py';original=t.read_bytes()
        t.write_bytes(b'bad')
        with pytest.raises(B.GuardError,match='context_bytes_changed'): B.validate_context(p)
        t.write_bytes(original);(Path(tmp)/'hardlink').hardlink_to(t)
        with pytest.raises(B.GuardError,match='context_file_mode_invalid'): B.validate_context(p)

def test_requires_explicit_execute():
    with patch.object(sys,'argv',['builder']),pytest.raises(B.GuardError,match='explicit_execute_required'):B.main()

def test_preflight_rejects_backend_drift_before_work():
    from unittest.mock import MagicMock
    R=MagicMock();R.inspect.return_value={'Id':'other','Image':B.IMAGE}
    with patch.object(B,'no_known_concurrency'),patch.object(B,'capacity'),pytest.raises(B.GuardError,match='backend_owner_changed'):
        B.preflight(R,{'baselines':{'backend':{}}})
    R.inventory.assert_not_called()

def test_preflight_rejects_unexpected_container_and_busy_gate():
    from unittest.mock import MagicMock
    import subprocess,json
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'gate.py').write_text('synthetic')
        R=MagicMock();R.ROOT=root;R.SUPPORT=root;R.GATES=['gate.py'];R.FINANCIAL_ANCHOR_MS=1
        current={'Id':B.CONTAINER,'Image':B.IMAGE,'State':{'Running':True,'Health':{'Status':'healthy'}}}
        R.inspect.return_value=current;R.H.container_signature.return_value={'id':B.CONTAINER}
        R.inventory.side_effect=lambda service,**kw: {'a':'1'};R.runtime_contract.return_value={};R.P.settings_sha.return_value='settings'
        plan={'baselines':{'backend':{'id':B.CONTAINER,'inventory':{'a':'1'},'settingsSha256':'settings'}},'webInventory':{'a':'1'},'nonTargets':{},'runtimeBefore':{}}
        with patch.object(B,'no_known_concurrency'),patch.object(B,'capacity'),patch.object(B,'run',return_value=subprocess.CompletedProcess([],0,b'other-container\n',b'')),pytest.raises(B.GuardError,match='container_set_changed'):
            B.preflight(R,plan)
        R.H.normalize_gate.return_value={'busy':1};R.H.gate_has_read_or_unknown_failure.return_value=False;R.H.gate_is_idle.return_value=False
        compose={str(root/f'path{i}'):'x' for i in range(20)}
        for name in compose:Path(name).write_bytes(b'synthetic')
        (root/'compose-hashes.json').write_text(json.dumps(compose))
        def fake_run(args,**kw):
            return subprocess.CompletedProcess(args,0,b'compose-backend-1\n' if args[1]=='ps' else b'{}',b'')
        with patch.object(B,'ROOT',root),patch.object(B,'no_known_concurrency'),patch.object(B,'capacity'),patch.object(B,'run',side_effect=fake_run),patch.object(Path,'is_file',return_value=True),patch.object(B,'sha',return_value='x'),pytest.raises(B.GuardError,match='protected_work_or_unknown'):
            B.preflight(R,plan)

def test_tampered_plan_never_loads_controller():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp).resolve();(root/'input.template.json').write_text('{}');(root/'compose-hashes.json').write_text('{}')
        with patch.object(B,'ROOT',root),patch.object(B,'load_controller') as load,patch.object(sys,'argv',['builder','--execute']),pytest.raises(B.GuardError,match='plan_source_changed'):
            B.main()
        load.assert_not_called()
