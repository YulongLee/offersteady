"""Synthetic policy/ownership tests; never access Docker, SSH or providers."""
from pathlib import Path
from copy import deepcopy
import ast,importlib.util,json,time
import pytest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'artifacts/global-cleanup-control-20261106'
if not (EVIDENCE/'baseline-public.json').exists():EVIDENCE=ROOT/'releases/20261106.1/global/review'
spec=importlib.util.spec_from_file_location('global_realtime_release_under_test',ROOT/'scripts/release_global_cleanup_control_20261106.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

@pytest.fixture
def plan(tmp_path,monkeypatch):
    e=EVIDENCE
    b=json.loads((e/'baseline-public.json').read_text())['backend']
    signature={k:v for k,v in b.items() if k not in {'inventory','settingsSha256','settingsFields','python','dependencies'}}
    before={**b,'signature':signature}
    schema=json.loads((e/'openapi.before.json').read_text())
    (tmp_path/'openapi.json').write_text(json.dumps(schema))
    schema_entry={'path':'openapi.json','schemaSha256':release.SCHEMA_SHA,'pathCount':223}
    files={'controller.py','base_helpers.py','ownership_primitives.py','probe.py','entity_idle_gate.py',*release.GATES,release.TCP_GATE}
    hashes={}
    for n in files:
        p=tmp_path/n;p.parent.mkdir(exist_ok=True,parents=True);p.write_text('synthetic public support\n');hashes[n]=release.digest(p.read_bytes())
    value={'releaseId':release.RELEASE,'baselines':{'backend':before},
        'candidates':{'backend':{'image':release.CANDIDATE_IMAGE,'inventory':json.loads((e/'candidate-manifest.json').read_text()),
            'rollbackImage':release.BASES['backend'][1],'rollbackInventory':b['inventory']}},
        'allowedBackend':release.APPROVED_BACKEND,'openapiBefore':schema_entry,'openapiAfter':schema_entry,
        'supportFiles':hashes,'publicRoutes':release.PUBLIC_ROUTES,'nonTargets':release.NON_TARGETS,
        'webInventory':release.WEB_INVENTORY,'runtimeBefore':release.RUNTIME_BEFORE,'ancillaryInputs':release.ANCILLARY_INPUTS}
    monkeypatch.setattr(release,'ROOT',tmp_path)
    (tmp_path/'input.json').write_text(json.dumps(value))
    return value

def test_exact_single_target_scope_accepted(plan):
    assert release.check_plan()==plan

@pytest.mark.parametrize('kind',['extra_field','wrong_release','web_target','old_image','rollback','source','extra_source','settings','schema','non_target','web_bytes','support','route','dependency','auxiliary'])
def test_drift_fails_closed(plan,kind):
    p=deepcopy(plan)
    if kind=='extra_field':p['ignoreBusy']=True
    if kind=='wrong_release':p['releaseId']='old'
    if kind=='web_target':p['candidates']['web']=p['candidates']['backend']
    if kind=='old_image':p['candidates']['backend']['image']=release.BASES['backend'][1]
    if kind=='rollback':p['candidates']['backend']['rollbackImage']=release.CANDIDATE_IMAGE
    if kind=='source':p['candidates']['backend']['inventory']['apps/backend/app/services/billing_service.py']='0'*64
    if kind=='extra_source':p['candidates']['backend']['inventory']['apps/backend/app/new.py']='0'*64
    if kind=='settings':p['baselines']['backend']['settingsFields']=344
    if kind=='schema':p['openapiAfter']={**p['openapiAfter'],'schemaSha256':'0'*64}
    if kind=='non_target':p['nonTargets']['offersteady-global-web-1']['image']='sha256:'+'0'*64
    if kind=='web_bytes':p['webInventory']['index.html']='0'*64
    if kind=='support':p['supportFiles']['controller.py']='0'*64
    if kind=='route':p['publicRoutes']['/new']='index.html'
    if kind=='dependency':p['runtimeBefore']['python']='3.13.15'
    if kind=='auxiliary':p['ancillaryInputs']={}
    (release.ROOT/'input.json').write_text(json.dumps(p))
    with pytest.raises(release.GuardError):release.check_plan()

def entity_counts():
    return {k:0 for k in ('activeCnBindings','activeCnCandidates','pendingCnCandidateClaims','recentCnEntityWrites',
      'unknownCnSessionStates','invalidCnEntityMetadata','cnEntityReadFailures','cnEntityScanLimitExceeded','cnEntityMutationDetected',
      'cnBoundBindings','cnStaleBindings','cnRetiredBindings','cnCandidates','cnRetiredCandidates','cnHistoricalEntities','scannedCnEntityRecords')}|{'atMs':int(time.time()*1000)}

@pytest.mark.parametrize('field',list(entity_counts()))
def test_all_protected_entity_fields_or_clock_are_validated(field,monkeypatch):
    value=entity_counts();value[field]=1 if field!='atMs' else 0
    monkeypatch.setattr(release,'save',lambda *a:None)
    protected={'activeCnBindings','activeCnCandidates','pendingCnCandidateClaims','recentCnEntityWrites','cnEntityMutationDetected'}
    unknown={'unknownCnSessionStates','invalidCnEntityMetadata','cnEntityReadFailures','cnEntityScanLimitExceeded','atMs'}
    if field in protected|unknown:
        with pytest.raises(release.GuardError):release.validate_entity_gate(value,75 if field in protected|unknown-{'atMs'} else 0)
    else:release.validate_entity_gate(value,0)

def test_no_entity_exception_or_unknown_field(monkeypatch):
    monkeypatch.setattr(release,'save',lambda *a:None)
    release.validate_entity_gate(entity_counts(),0)
    with pytest.raises(release.GuardError):release.validate_entity_gate(entity_counts()|{'ignoreTcp':1},0)
    with pytest.raises(release.GuardError):release.validate_entity_gate(entity_counts(),75)

def test_idle_order_preserves_seven_gates_and_adds_entity_gate(monkeypatch):
    seen=[]
    monkeypatch.setattr(release,'verify_single_writer',lambda:seen.append('single'))
    monkeypatch.setattr(release.P,'idle_gates',lambda m:seen.append('seven') or ['original'])
    monkeypatch.setattr(release,'entity_idle_gate',lambda m:seen.append('entity'))
    assert release.idle_gates({})==['original'] and seen==['single','seven','entity']

def test_gate_failure_never_skips_to_switch(monkeypatch):
    monkeypatch.setattr(release,'verify_single_writer',lambda:None)
    monkeypatch.setattr(release.P,'idle_gates',lambda m:(_ for _ in ()).throw(release.GuardError('protected_user_work_cutover_deferred')))
    monkeypatch.setattr(release,'entity_idle_gate',lambda m:pytest.fail('gate failure must stop'))
    with pytest.raises(release.GuardError,match='protected_user_work_cutover_deferred'):release.idle_gates({})

def functions(path):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

@pytest.mark.parametrize('name',['targets_owned','baseline_stopped_proof','check_non_targets','check_files','verify_sources',
 'tcp_gate','reconcile_intent','refresh_static_proxies','switch','restore_stopped_baseline','release_lock','relative_file','valid_inventory','gate_command'])
def test_lifecycle_and_ownership_primitives_unchanged(name):
    assert functions(ROOT/'scripts/release_global_realtime_20261104.py')[name]==functions(ROOT/'scripts/release_global_cleanup_control_20261106.py')[name]
