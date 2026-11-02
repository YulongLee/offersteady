"""Pinned Global performance/companion136 release; run only on Global host.

Default action is preflight. This controller calls no historical deployment
entrypoint. Private configuration snapshots and command diagnostics stay on the
server; output is fixed aggregate release evidence. No user work is terminated.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import time
from urllib.request import Request, urlopen

ROOT = Path('/opt/offersteady-global/releases/20261102-global-performance-companion-136-1')
RELEASE = '20261102-global-performance-companion-136-1'
PROJECT = 'offersteady-global'
_LOCAL_SUPPORT = Path(__file__).parent / 'release_support/global_performance_companion_136'
SUPPORT = _LOCAL_SUPPORT if _LOCAL_SUPPORT.is_dir() else Path(__file__).parent
BASES = {
    'backend': ('7bc15c77cef86681d068d6157270f87338d0cab9f1b14c8cddf7d11e83ad7536', 'sha256:63f8243bacfc075cd399032ec5ca05f669356cd087b5d57583a9ce08b474e066'),
    'web': ('6e4bd43d80c1d7f5b5959c3455fc423ca07efd304ef4210a02f2b0b16aa0629d', 'sha256:7f5fd6640aaea0b742eddb6227c41ddb7a0a0390fbe657486fdfef86efd38ad6'),
}
# Exact historical stopped build container, independently matched against the
# October22 frozen non-target. Its existence is preserved; no lifecycle action
# for this container is authorized by this release.
LEGACY_STOPPED_NAME = 'zealous_bhaskara'
LEGACY_STOPPED_SIGNATURE = {
    'id': 'b26658773fe6a73626510cba0116d31bb3154d1fb554ca521deb254ef21ef57a',
    'image': 'sha256:414cfd1c18647de7db5857d6cadb64e46d7e8508c837e7d5e639a682800a3e47',
    'imageReference': 'sha256:414cfd1c18647de7db5857d6cadb64e46d7e8508c837e7d5e639a682800a3e47',
    'startedAt': '2026-09-07T09:39:55.330513404Z',
    'health': None, 'running': False, 'restartCount': 0,
    'configSha256': '0d694f0b69eaa0caa369fe2588e9d2ed89bbb17be2783f02cd3bb22f2efc24ea',
    'hostConfigSha256': '229cb2b629d3fd0630052e491427c9fd2382d6f4bc74fba1d1a66f4e3e952126',
    'mountsSha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
    'networkSettingsSha256': '141afbcf56bd0eb2fe360776ff29c34e173b5e3a300da1c994721fe9a068fddd',
    'networks': ['bridge'],
}
EXPECTED_NAMES = {PROJECT+'-'+name+'-1' for name in ('backend','web','material-worker','admin','analytics','postgres','redis')} | {LEGACY_STOPPED_NAME}
BACKEND_FILES = {
    'apps/backend/app/modules/web.py', 'apps/backend/app/services/document_service.py',
    'apps/backend/app/services/session_service.py', 'apps/backend/app/ports/interview_session.py',
    'apps/backend/app/services/interview_session_repository.py',
    'apps/backend/app/services/postgres_interview_session_repository.py',
    'apps/backend/app/services/realtime_speech_service.py', 'apps/backend/app/modules/screenshot_answer.py',
}
MANIFEST = 'apps/backend/app/global_desktop_release_manifest.json'
HISTORY = 'apps/backend/app/global_desktop_release_history.json'
NEXT_PATH = '/api/v1/screenshot-answer/desktop-devices/{device_id}/capture-requests/next'
FINANCIAL_ANCHOR_MS = 1792604406734  # original actual Backend start, never a candidate restart
GATES = ('legacy-gates/check-idle.py','legacy-gates/check-mock-idle.py','global_mock_companion_idle_gate.py',
         'extra_idle_gate.py','active_work_gate.py','resume_optimizer_idle_gate.py','global_financial_idle_gate.py')
TCP_GATE = 'backend_tcp_idle_gate.py'
TARGETS = {('macos','arm64'),('macos','x64'),('windows','x64')}
SHA = re.compile('[0-9a-f]{64}')
IMAGE = re.compile('sha256:[0-9a-f]{64}')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


H = load_module(SUPPORT/'base_helpers.py', 'global_perf136_helpers')
P = load_module(SUPPORT/'ownership_primitives.py', 'global_perf136_ownership')
GuardError, require, digest, canonical = H.GuardError, H.require, H.digest, H.canonical
run, inspect, environment, read_json = H.run, H.inspect, H.environment, H.read_json
write_json = P.atomic_write_json


def save(name, value):
    write_json(ROOT/name, value)


def emit(**value):
    print(json.dumps(value, separators=(',',':')), flush=True)


def bind_primitives():
    H.ROOT, H.PROJECT, H.write_json = ROOT, PROJECT, write_json
    values = dict(ROOT=ROOT,SUPPORT=SUPPORT,PROJECT=PROJECT,BASES=BASES,H=H,GuardError=GuardError,
                  require=require,digest=digest,canonical=canonical,run=run,inspect=inspect,
                  environment=environment,read_json=read_json,save=save,GATES=GATES,TCP_GATE=TCP_GATE,
                  expected_environment=lambda before, service, kind: dict(environment(before)),
                  targets_owned=targets_owned,gate_command=gate_command)
    for name,value in values.items():
        setattr(P,name,value)


def relative_file(value):
    require(isinstance(value,str) and value and str(PurePosixPath(value))==value
            and not PurePosixPath(value).is_absolute() and '..' not in PurePosixPath(value).parts,
            'invalid_release_relative_path')
    p=ROOT/value
    require(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT.resolve()), 'release_input_file_missing_or_linked')
    return p


def valid_inventory(value):
    require(isinstance(value,dict) and value, 'inventory_missing')
    for name,checksum in value.items():
        require(isinstance(name,str) and str(PurePosixPath(name))==name and not PurePosixPath(name).is_absolute()
                and '..' not in PurePosixPath(name).parts and isinstance(checksum,str) and SHA.fullmatch(checksum), 'invalid_inventory_entry')


def check_schema_delta(before, after):
    stripped=deepcopy(after)
    try:
        old=before['paths'][NEXT_PATH]['get'].get('parameters',[])
        new=stripped['paths'][NEXT_PATH]['get']['parameters']
        extra=[p for p in new if p.get('in')=='query' and p.get('name') in {'sessionId','requestId'}]
        require(len(extra)==2 and {p['name'] for p in extra}=={'sessionId','requestId'}
                and all(p.get('required') is False for p in extra), 'optional_query_contract_changed')
        require(not any(p.get('name') in {'sessionId','requestId'} and p.get('in')=='query' for p in old), 'query_already_in_baseline')
        stripped['paths'][NEXT_PATH]['get']['parameters']=[p for p in new if p not in extra]
        require(stripped==before, 'api_contract_changed_outside_optional_queries')
    except (KeyError,TypeError):
        raise GuardError('optional_query_contract_missing') from None


def validate_manifest(payload, proofs):
    require(isinstance(payload,dict) and payload.get('version')==1 and type(payload.get('generatedAtMs')) is int
            and payload['generatedAtMs']>0 and isinstance(payload.get('entries'),list) and len(payload['entries'])==3,
            'global_manifest_incomplete')
    require(isinstance(proofs,list) and len(proofs)==3, 'object_readback_proofs_missing')
    seen=set()
    for entry in payload['entries']:
        target=(entry.get('platform'),entry.get('architecture'))
        require(all(isinstance(x,str) for x in target) and target in TARGETS and target not in seen, 'global_manifest_targets_invalid')
        seen.add(target)
        platform,arch=target
        name=('OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe' if platform=='windows'
              else f'OfferSteady-Companion-Global-1.3.6-macOS-{arch}.dmg')
        require(entry.get('version')=='1.3.6' and entry.get('protocolVersion')=='2.0'
                and entry.get('fileName')==name and entry.get('objectKey')==f'global-desktop-releases/{platform}/{arch}/1.3.6/{name}'
                and entry.get('distributionStatus')=='published' and entry.get('developmentOnly') is False
                and type(entry.get('fileSizeBytes')) is int and 0<entry['fileSizeBytes']<2_000_000_000
                and isinstance(entry.get('sha256'),str) and SHA.fullmatch(entry['sha256'])
                and entry.get('publishedAtMs')==payload['generatedAtMs'], 'global_manifest_metadata_invalid')
        require(not any(k in entry for k in ('localPath','artifactPath','zipPath')), 'private_metadata_in_manifest')
        require((entry.get('signingStatus')=='verified' and entry.get('notarized') is True and entry.get('minimumOs')=='macOS 14.2+')
                if platform=='macos' else
                (entry.get('signingStatus')=='unsigned' and entry.get('notarized') is False and entry.get('minimumOs')=='Windows 10 22H2+'), 'artifact_trust_metadata_invalid')
        matches=[p for p in proofs if (p.get('platform'),p.get('architecture'))==target]
        require(len(matches)==1 and matches[0].get('objectReadbackVerified') is True
                and matches[0].get('contentType')==('application/x-apple-diskimage' if platform=='macos' else 'application/vnd.microsoft.portable-executable')
                and all(matches[0].get(k)==entry.get(k) for k in ('version','fileName','fileSizeBytes','sha256','objectKey')), 'object_readback_does_not_match_manifest')
    require(seen==TARGETS, 'global_manifest_targets_missing')


def check_plan():
    plan=read_json(ROOT/'input.json')
    require(set(plan)=={'releaseId','baselines','candidates','allowedBackend','allowedWebChanged','globalManifest',
                        'objectsReadback','openapiBefore','openapiAfter','supportFiles','publicRoutes','nonTargets'}, 'input_fields_changed')
    require(plan['releaseId']==RELEASE and set(plan['baselines'])==set(BASES)
            and set(plan['candidates'])==set(BASES), 'component_scope_changed')
    for service,(cid,image) in BASES.items():
        b,c=plan['baselines'][service],plan['candidates'][service]
        require((b.get('id'),b.get('image'))==(cid,image) and isinstance(b.get('startedAt'),str), 'actual_component_baseline_changed')
        require(isinstance(b.get('signature'),dict) and b['signature'].get('id')==cid
                and b['signature'].get('image')==image and b['signature'].get('startedAt')==b['startedAt'], 'runtime_signature_baseline_missing')
        valid_inventory(b.get('inventory'));valid_inventory(c.get('inventory'));valid_inventory(c.get('rollbackInventory'))
        require(len(b['inventory'])==(302 if service=='backend' else 235), 'actual_inventory_scope_changed')
        require(all(isinstance(c.get(k),str) and IMAGE.fullmatch(c[k]) for k in ('image','rollbackImage')), 'candidate_fixed_images_required')
        require(c['image']!=image, 'candidate_missing')
        if service=='backend':
            require(isinstance(b.get('settingsSha256'),str) and SHA.fullmatch(b['settingsSha256'])
                    and type(b.get('settingsFields')) is int and b['settingsFields']>0, 'settings_baseline_missing')
        else:
            require(isinstance(b.get('nginxSha256'),str) and SHA.fullmatch(b['nginxSha256']), 'nginx_baseline_missing')
    b,c=plan['baselines']['backend']['inventory'],plan['candidates']['backend']
    require(set(plan['allowedBackend'])==BACKEND_FILES|{MANIFEST,HISTORY}, 'backend_allowlist_changed')
    require(set(c['inventory'])==set(b)|{HISTORY} and set(c['rollbackInventory'])==set(c['inventory']), 'backend_input_set_changed')
    require({p for p in c['inventory'] if c['inventory'][p]!=b.get(p)}==set(plan['allowedBackend'])
            and all(c['inventory'][p]==h for p,h in plan['allowedBackend'].items()), 'backend_delta_not_exact')
    require({p for p in c['rollbackInventory'] if c['rollbackInventory'][p]!=b.get(p)}=={MANIFEST,HISTORY,'apps/backend/app/modules/web.py'}
            and all(c['rollbackInventory'][p]==c['inventory'][p] for p in (MANIFEST,HISTORY)), 'backend_compatibility_rollback_changed')
    b,c=plan['baselines']['web']['inventory'],plan['candidates']['web']
    require(set(b)<=set(c['inventory']), 'old_static_assets_removed')
    changed={p for p in b if b[p]!=c['inventory'][p]}
    require(changed==set(plan['allowedWebChanged']) and 'index.html' in changed
            and all(p.endswith('.html') or p=='offersteady-global-build.json' for p in changed), 'web_mutable_scope_changed')
    extra=set(c['inventory'])-set(b)
    require(extra and all(re.fullmatch(r'assets/[A-Za-z0-9_.-]+\.js',p) for p in extra), 'web_new_asset_scope_changed')
    require(c['rollbackInventory']=={**b,**{p:c['inventory'][p] for p in extra}}, 'web_rollback_not_compatible')
    public_manifest=relative_file(plan['globalManifest']['path'])
    require(digest(public_manifest.read_bytes())==plan['globalManifest']['sha256']==plan['candidates']['backend']['inventory'][MANIFEST], 'candidate_manifest_drift')
    validate_manifest(read_json(public_manifest),plan['objectsReadback'])
    schemas=[]
    for k in ('openapiBefore','openapiAfter'):
        document=read_json(relative_file(plan[k]['path']))
        require(digest(canonical(document))==plan[k]['schemaSha256'] and len(document.get('paths',{}))==plan[k]['pathCount'], 'schema_input_drift')
        schemas.append(document)
    check_schema_delta(*schemas)
    expected={'controller.py','base_helpers.py','ownership_primitives.py','probe.py',*GATES,TCP_GATE}
    require(set(plan['supportFiles'])==expected, 'release_support_scope_changed')
    for path,checksum in plan['supportFiles'].items():
        require(isinstance(checksum,str) and SHA.fullmatch(checksum)
                and digest(relative_file(path).read_bytes())==checksum, 'release_support_drift')
    require(isinstance(plan['publicRoutes'],dict) and plan['publicRoutes'].get('/')=='index.html'
            and plan['publicRoutes'].get('/login')=='index.html'
            and all(isinstance(p,str) and p.startswith('/') and not p.startswith('//') and '?' not in p
                    and name in plan['candidates']['web']['inventory'] for p,name in plan['publicRoutes'].items()), 'public_route_contract_invalid')
    require(isinstance(plan['nonTargets'],dict)
            and set(plan['nonTargets'])==EXPECTED_NAMES-{PROJECT+'-'+s+'-1' for s in BASES}
            and all(isinstance(v,dict) and IMAGE.fullmatch(v.get('image','')) for v in plan['nonTargets'].values()), 'non_target_baseline_missing')
    require(plan['nonTargets'][LEGACY_STOPPED_NAME]==LEGACY_STOPPED_SIGNATURE, 'historical_stopped_baseline_changed')
    return plan


def expected_inventory(plan, service, kind):
    if kind=='baseline':
        return plan['baselines'][service]['inventory']
    return plan['candidates'][service]['inventory' if kind=='new' else 'rollbackInventory']


def progress_state():
    return read_json(ROOT/'progress.json') if (ROOT/'progress.json').exists() else {}


def baseline_stopped_proof(service,current):
    before=read_json(ROOT/service/'container-before.json')
    require((current['Id'],current['Image'])==BASES[service]
            and P.ownership_signature(current)==P.ownership_signature(before) and H.stopped_process(current), 'baseline_stopped_owner_unproven')
    again=inspect(current['Id'])
    require(H.stopped_process(again) and H.container_signature(again)==H.container_signature(current), 'baseline_stopped_owner_unstable')


def targets_owned(manifest,progress,*,recovery=False):
    restored=read_json(ROOT/'baseline-restores.json') if (ROOT/'baseline-restores.json').exists() else {}
    for service,target in manifest['targets'].items():
        current=inspect(target['container']);entry=progress.get(service)
        if entry:
            require((current['Id'],current['Image'])==(entry['id'],entry['image']), 'release_container_owner_changed')
            P.assert_context_owner(current,target,entry['kind'])
            same={k:v for k,v in H.container_signature(current).items() if k!='health'}=={k:v for k,v in entry['signature'].items() if k!='health'}
            if not same and recovery:
                P.recovery_process_proof(current,entry)
            else:
                require(same,'released_container_signature_changed')
        elif recovery and not current['State']['Running']:
            baseline_stopped_proof(service,current)
        else:
            before=read_json(ROOT/service/'container-before.json')
            require((current['Id'],current['Image'])==BASES[service] and P.ownership_signature(current)==P.ownership_signature(before), 'baseline_container_owner_changed')
            reference=restored[service]['signature'] if service in restored else H.container_signature(before)
            require({k:v for k,v in H.container_signature(current).items() if k!='health'}=={k:v for k,v in reference.items() if k!='health'}, 'baseline_signature_changed')


def check_non_targets(manifest):
    names=set(run(['docker','ps','-a','--format','{{.Names}}']).stdout.decode().splitlines())
    require(names==EXPECTED_NAMES, 'non_target_container_set_changed')
    require(set(manifest['nonTargets'])==EXPECTED_NAMES-{PROJECT+'-'+s+'-1' for s in BASES}, 'non_target_manifest_set_changed')
    for name,signature in manifest['nonTargets'].items():
        now=H.container_signature(inspect(name))
        if name==LEGACY_STOPPED_NAME:
            require(signature==LEGACY_STOPPED_SIGNATURE and now==LEGACY_STOPPED_SIGNATURE, 'historical_stopped_container_changed')
        require({k:v for k,v in now.items() if k!='health'}=={k:v for k,v in signature.items() if k!='health'}, 'non_target_container_changed')
    for name,tree in manifest['nonTargetNginx'].items():
        require(P.nginx_inputs(container=name)==tree, 'non_target_nginx_drift')


def check_files(manifest,plan):
    require(digest((ROOT/'input.json').read_bytes())==manifest['inputSha256'], 'input_manifest_drift')
    require(manifest.get('financialAnchorMs')==FINANCIAL_ANCHOR_MS, 'financial_anchor_changed')
    for relative,checksum in manifest['privateFiles'].items():
        require(digest(relative_file(relative).read_bytes())==checksum, 'private_snapshot_drift')
    for service,target in manifest['targets'].items():
        before=read_json(ROOT/service/'container-before.json');H.verify_frozen_files(target,before)
        for path,checksum in target['sourceHashes'].items():
            require(digest(Path(path).read_bytes())==checksum, 'production_compose_or_env_drift')
        require(digest(canonical(H.rendered(target)))==target['sourceRenderedSha'], 'production_render_drift')
        for kind in ('new','rollback'):
            overlay=Path(target[kind+'Overlay'])
            require(digest(overlay.read_bytes())==target[kind+'OverlaySha256'], 'release_overlay_drift')
            require(H.rendered(target,frozen=True,overlay=overlay)==H.expected_overlay(read_json(ROOT/service/'rendered-before.json'),service,target[kind+'Image']), 'unrelated_rendered_configuration_change')
    check_non_targets(manifest)


def stopped_web_inventory(current):
    response=run(['docker','cp',current['Id']+':/usr/share/nginx/html/.','-'],timeout=30)
    require(len(response.stdout)<=200*1024*1024, 'stopped_web_archive_too_large')
    result={}
    with tarfile.open(fileobj=io.BytesIO(response.stdout),mode='r:*') as archive:
        for member in archive:
            name=PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts, 'stopped_web_archive_unsafe')
            if member.isdir():
                continue
            require(member.isfile() and 0<=member.size<=100*1024*1024, 'stopped_web_archive_entry_invalid')
            key=str(name)
            if key.startswith('html/'):
                key=key[5:]
            require(key and key not in result, 'stopped_web_archive_duplicate')
            data=archive.extractfile(member).read();require(len(data)==member.size, 'stopped_web_archive_truncated')
            result[key]=digest(data)
    return result


def verify_sources(manifest,plan,progress,*,recovery=False):
    targets_owned(manifest,progress,recovery=recovery)
    for service,target in manifest['targets'].items():
        current=inspect(target['container']);kind=progress.get(service,{}).get('kind','baseline')
        if current['State']['Running']:
            actual=P.inventory(service)
        else:
            require(recovery, 'unexpected_stopped_target')
            if service not in progress:
                baseline_stopped_proof(service,current)
            else:
                require(H.stopped_process(current) and P.ownership_signature(current)==progress[service]['ownershipSignature'], 'stopped_source_owner_unproven')
            actual=stopped_web_inventory(current) if service=='web' else P.stopped_source_inventory(current)
            again=inspect(current['Id']);require(H.stopped_process(again) and H.container_signature(again)==H.container_signature(current), 'stopped_source_owner_unstable')
        require(actual==expected_inventory(plan,service,kind), 'runtime_source_drift')


def verify_runtime(manifest,plan,progress,*,final=False):
    targets_owned(manifest,progress);check_files(manifest,plan);verify_sources(manifest,plan,progress)
    for service,target in manifest['targets'].items():
        current=inspect(target['container']);kind=progress.get(service,{}).get('kind','baseline')
        require(current['State']['Running'] and current['RestartCount']==0, 'target_not_running')
        if service=='backend':
            require(current['State'].get('Health',{}).get('Status')=='healthy', 'backend_unhealthy')
            require(P.settings(service)==read_json(ROOT/service/'settings-before.private.json'), 'effective_settings_drift')
        else:
            require(P.nginx_inputs(container=current['Id'])==read_json(ROOT/'web/nginx-before.json'), 'runtime_nginx_drift')
        if service in progress:
            P.runtime_invariant(read_json(ROOT/service/'container-before.json'),current,target,kind)
        if final:
            require(kind=='new', 'partial_release_not_complete')
    expected=plan['openapiAfter'] if progress.get('backend',{}).get('kind')=='new' else plan['openapiBefore']
    actual=P.schema();require(digest(canonical(actual))==expected['schemaSha256'] and len(actual['paths'])==expected['pathCount'], 'runtime_api_schema_drift')


def candidate_probe(target,plan,*,rollback=False):
    command=['docker','run','--rm','-i','--network','none','--read-only','--cap-drop','ALL',
             '--security-opt','no-new-privileges','--pids-limit','64','--memory','512m',
             '--env-file',str(ROOT/'backend/runtime.env.private'),'-v',str(ROOT)+':/release:ro',
             '--workdir','/app/apps/backend','--entrypoint','python',target['rollbackImage'] if rollback else target['newImage'],'-B','-',
             '--baseline-settings','/release/backend/settings-before.private.json',
             '--baseline-schema','/release/'+plan['openapiBefore']['path']]
    if rollback:command.append('--rollback')
    result=json.loads(run(command,input=(SUPPORT/'probe.py').read_bytes(),timeout=60).stdout)
    require(set(result)=={'passed','checks','providerCalls','databaseWrites','workersStarted','lifespanStarted','settingsUnchanged','schemaAllowedDelta'}
            and result.get('passed') is True and result.get('settingsUnchanged') is True and result.get('schemaAllowedDelta') is True
            and result.get('lifespanStarted') is False and all(type(result.get(k)) is int and result[k]==0 for k in ('providerCalls','databaseWrites','workersStarted'))
            and isinstance(result.get('checks'),list) and result['checks'] and all(isinstance(k,str) and re.fullmatch('[a-z0-9_]+',k) for k in result['checks']), 'candidate_offline_probe_failed')
    save('backend/offline-probe-'+('rollback' if rollback else 'new')+'.json',result)


def prepare():
    plan=check_plan();require(not (ROOT/'prepared.json').exists(), 'already_prepared')
    names=set(run(['docker','ps','-a','--format','{{.Names}}']).stdout.decode().splitlines());require(names==EXPECTED_NAMES, 'baseline_container_set_changed')
    require(H.container_signature(inspect(LEGACY_STOPPED_NAME))==LEGACY_STOPPED_SIGNATURE,
            'historical_stopped_container_changed')
    manifest={'inputSha256':digest((ROOT/'input.json').read_bytes()),'financialAnchorMs':FINANCIAL_ANCHOR_MS,
              'targets':{},'nonTargets':{},'nonTargetNginx':{},'privateFiles':{},'proxyStaticBackendUpstreams':{}}
    require(digest(canonical(P.schema()))==plan['openapiBefore']['schemaSha256'], 'fresh_api_schema_drift')
    for service,(cid,image) in BASES.items():
        before=inspect(PROJECT+'-'+service+'-1');b=plan['baselines'][service];c=plan['candidates'][service]
        require((before['Id'],before['Image'],before['State']['StartedAt'])==(cid,image,b['startedAt'])
                and before['State']['Running'] and before['RestartCount']==0, 'fresh_runtime_baseline_changed')
        require(H.container_signature(before)==b['signature'], 'fresh_runtime_signature_changed')
        require(P.inventory(service)==b['inventory']==P.inventory(service,image=image), 'writable_layer_or_baseline_drift')
        target=H.freeze(before,service)
        target.update(newImage=c['image'],rollbackImage=c['rollbackImage'])
        if service=='backend':
            settings=P.settings(service)
            require(digest(canonical(settings))==b['settingsSha256'] and len(settings)==b['settingsFields'], 'settings_baseline_drift')
            save('backend/settings-before.private.json',settings);P.write_env(ROOT/'backend/runtime.env.private',environment(before))
        else:
            tree=P.nginx_inputs(container=before['Id']);require(tree==P.nginx_inputs(image=image), 'web_nginx_writable_drift')
            require(digest(H.read_container(before['Id'],'/etc/nginx/conf.d/default.conf'))==b['nginxSha256'], 'web_nginx_baseline_drift')
            save('web/nginx-before.json',tree)
        for kind,field in (('new','image'),('rollback','rollbackImage')):
            candidate=inspect(c[field]);H.verify_image_base(candidate,inspect(image))
            require(P.inventory(service,image=c[field])==expected_inventory(plan,service,kind), 'candidate_inventory_drift')
            if service=='web':
                require(P.nginx_inputs(image=c[field])==tree, 'candidate_nginx_drift')
            overlay=ROOT/service/(kind+'.compose.json');write_json(overlay,{'services':{service:{'image':c[field]}}})
            target[kind+'Overlay']=str(overlay);target[kind+'OverlaySha256']=digest(overlay.read_bytes())
            require(H.rendered(target,frozen=True,overlay=overlay)==H.expected_overlay(read_json(ROOT/service/'rendered-before.json'),service,c[field]), 'candidate_compose_configuration_changed')
        manifest['targets'][service]=target
    candidate_probe(manifest['targets']['backend'],plan)
    candidate_probe(manifest['targets']['backend'],plan,rollback=True)
    for name in names-{t['container'] for t in manifest['targets'].values()}:
        manifest['nonTargets'][name]=H.container_signature(inspect(name))
        require(manifest['nonTargets'][name]==plan['nonTargets'][name], 'fresh_non_target_signature_changed')
    manifest['nonTargetNginx'][PROJECT+'-admin-1']=P.nginx_inputs(container=PROJECT+'-admin-1')
    for name in (PROJECT+'-web-1',PROJECT+'-admin-1'):
        raw=run(['docker','exec',name,'nginx','-T']).stdout
        manifest['proxyStaticBackendUpstreams'][name]=bool(re.search(rb'(?m)^\s*(?:proxy_pass\s+https?://|server\s+)(?:backend|offersteady-global-backend-1)(?::8000)?(?:[;/\s])',raw))
    for service in BASES:
        for p in (ROOT/service).rglob('*'):
            if p.is_file() and p.name not in {'new.compose.json','rollback.compose.json'}:
                manifest['privateFiles'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
    save('prepared.json',manifest);verify_runtime(manifest,plan,{})
    emit(prepared=True,productionChanged=False,components=2,financialAnchorMs=FINANCIAL_ANCHOR_MS)


def gate_command(manifest):
    require(manifest.get('financialAnchorMs')==FINANCIAL_ANCHOR_MS, 'financial_anchor_changed')
    before=read_json(ROOT/'backend/container-before.json');network=before['HostConfig']['NetworkMode']
    require(isinstance(network,str) and re.fullmatch('[A-Za-z0-9_.-]+',network) and network not in {'host','none'}, 'gate_network_invalid')
    return ['docker','run','--rm','-i','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--pids-limit','64','--memory','512m','--network',network,'--env-file',str(ROOT/'backend/runtime.env.private'),
            '-e','OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS='+str(FINANCIAL_ANCHOR_MS),
            '--workdir','/app/apps/backend','--entrypoint','python',BASES['backend'][1],'-B','-']


def idle_gates(manifest):
    return P.idle_gates(manifest)


def tcp_gate(manifest,progress,*,recovery=False):
    current=inspect(PROJECT+'-backend-1')
    if recovery and 'backend' not in progress and not current['State']['Running']:
        baseline_stopped_proof('backend',current)
        save('last-tcp-idle-gate.json',{'passed':True,'method':'twice_proven_stopped_baseline'})
        return
    return P.tcp_gate(manifest,progress,recovery=recovery)


def reconcile_intent(manifest,progress):
    path=ROOT/'switch-intent.json'
    if not path.exists():return
    intent=read_json(path)
    if progress!=intent['previousProgress']:return
    service,kind=intent['service'],intent['kind'];require(service in BASES and kind in {'new','rollback'}, 'switch_intent_invalid')
    target=manifest['targets'][service];now=inspect(target['container'])
    if now['Image']==target[kind+'Image'] and now['Config']['Labels'].get('com.docker.compose.project.config_files')==','.join(target['frozenComposeFiles']+[target[kind+'Overlay']]):
        P.record_created_owner(target,kind,intent['beforeId'],now,progress)


def refresh_static_proxies(manifest,plan,progress):
    check_plan();check_files(manifest,plan);verify_sources(manifest,plan,progress)
    idle_gates(manifest);tcp_gate(manifest,progress)
    refreshed=[]
    for name,needed in manifest['proxyStaticBackendUpstreams'].items():
        require(name in {PROJECT+'-web-1',PROJECT+'-admin-1'} and type(needed) is bool, 'proxy_refresh_scope_changed')
        if needed:
            check_non_targets(manifest);targets_owned(manifest,progress)
            run(['docker','exec',name,'nginx','-t']);run(['docker','exec',name,'nginx','-s','reload'])
            check_non_targets(manifest);targets_owned(manifest,progress);refreshed.append(name)
    save('proxy-refresh.json',{'proxyReloaded':refreshed,'onlyAfterBackendIpChange':True,'configurationChanged':False})


def switch(manifest,plan,progress,service,kind):
    require(service in BASES and kind in {'new','rollback'}, 'switch_scope_invalid')
    check_plan();check_files(manifest,plan);verify_sources(manifest,plan,progress,recovery=kind=='rollback')
    idle_gates(manifest);tcp_gate(manifest,progress,recovery=kind=='rollback')
    check_plan();check_files(manifest,plan);targets_owned(manifest,progress,recovery=kind=='rollback')
    target=manifest['targets'][service];before=inspect(target['container'])
    save('switch-intent.json',{'service':service,'kind':kind,'beforeId':before['Id'],'previousProgress':deepcopy(progress)})
    try:
        run(H.compose_args(target,frozen=True,overlay=target[kind+'Overlay'])+['up','-d','--no-build','--no-deps','--pull','never',service],timeout=120)
    finally:
        now=inspect(target['container'])
        if now['Image']==target[kind+'Image'] and now['Config']['Labels'].get('com.docker.compose.project.config_files')==','.join(target['frozenComposeFiles']+[target[kind+'Overlay']]):
            P.record_created_owner(target,kind,before['Id'],now,progress)
            P.runtime_invariant(read_json(ROOT/service/'container-before.json'),now,target,kind)
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        now=inspect(target['container'])
        if now['State']['Running'] and now['RestartCount']==0 and (service!='backend' or now['State'].get('Health',{}).get('Status')=='healthy'):break
        time.sleep(1)
    else:raise GuardError('target_health_failed')
    P.runtime_invariant(read_json(ROOT/service/'container-before.json'),now,target,kind)
    require(P.inventory(service)==expected_inventory(plan,service,kind), 'released_source_drift')
    if service=='backend':
        ips=lambda item:{n:v.get('IPAddress') for n,v in item['NetworkSettings']['Networks'].items()}
        if ips(before)!=ips(now):refresh_static_proxies(manifest,plan,progress)


def public_checks(plan,progress):
    kind=progress.get('web',{}).get('kind','baseline');files=expected_inventory(plan,'web',kind)
    for path,name in plan['publicRoutes'].items():
        # A partial release may never have switched Web. Its exact baseline
        # cannot serve new-only assets yet; do not recreate it merely to make
        # recovery diagnostics pass. New and compatible rollback verify all.
        if kind=='baseline' and name not in files:continue
        with urlopen(Request('https://offersteady.com'+path,headers={'Cache-Control':'no-cache','Accept-Encoding':'identity'}),timeout=15) as response:
            require(response.status==200 and digest(response.read())==files[name], 'public_route_bytes_changed')
    with urlopen('https://offersteady.com/healthz',timeout=15) as response:
        require(response.status==200 and json.load(response)['data']['status']=='ok', 'public_health_failed')


def verify():
    plan=check_plan();manifest=read_json(ROOT/'prepared.json');progress=progress_state();reconcile_intent(manifest,progress)
    verify_runtime(manifest,plan,progress,final=True);public_checks(plan,progress)
    save('verified.json',{'atMs':int(time.time()*1000),'verified':True,'services':list(BASES),'nonTargetsUnchanged':True})
    emit(verified=True,components=2,nonTargetsUnchanged=True,financialAnchorMs=FINANCIAL_ANCHOR_MS)


def restore_stopped_baseline(manifest,plan,progress,service):
    current=inspect(manifest['targets'][service]['container']);baseline_stopped_proof(service,current)
    check_files(manifest,plan);verify_sources(manifest,plan,progress,recovery=True);idle_gates(manifest);tcp_gate(manifest,progress,recovery=True)
    baseline_stopped_proof(service,inspect(current['Id']))
    try:run(['docker','start',current['Id']],timeout=60)
    finally:
        now=inspect(current['Id'])
        if now['State']['Running']:
            require(P.ownership_signature(now)==P.ownership_signature(current), 'restored_baseline_owner_changed')
            restores=read_json(ROOT/'baseline-restores.json') if (ROOT/'baseline-restores.json').exists() else {}
            restores[service]={'id':now['Id'],'image':now['Image'],'signature':H.container_signature(now)};save('baseline-restores.json',restores)


def rollback():
    plan=check_plan();manifest=read_json(ROOT/'prepared.json');progress=progress_state();reconcile_intent(manifest,progress)
    check_files(manifest,plan);verify_sources(manifest,plan,progress,recovery=True)
    for service in ('backend','web'):
        if service not in progress and not inspect(manifest['targets'][service]['container'])['State']['Running']:
            restore_stopped_baseline(manifest,plan,progress,service)
    for service in ('backend','web'):
        if progress.get(service,{}).get('kind')=='new':switch(manifest,plan,progress,service,'rollback')
    verify_runtime(manifest,plan,progress);require(all(p['kind']=='rollback' for p in progress.values()), 'rollback_incomplete')
    public_checks(plan,progress);save('rolled-back.json',{'restored':True,'atMs':int(time.time()*1000)})
    emit(rollbackSucceeded=True,compatibilityDownloadsPreserved=True)


def deploy(*,preflight=False):
    plan=check_plan();manifest=read_json(ROOT/'prepared.json');progress=progress_state();reconcile_intent(manifest,progress)
    require(not (ROOT/'rolled-back.json').exists(), 'release_already_rolled_back')
    if (ROOT/'deployed.json').exists():
        verify();return emit(alreadyDeployed=True,productionChanged=False)
    if all(progress.get(s,{}).get('kind')=='new' for s in BASES):
        verify_runtime(manifest,plan,progress,final=True);public_checks(plan,progress)
        if not preflight:save('deployed.json',{'deployed':True,'atMs':int(time.time()*1000),'reconciledCompletedSwitch':True})
        return emit(alreadyDeployed=True,productionChanged=False)
    verify_runtime(manifest,plan,progress);idle_gates(manifest);tcp_gate(manifest,progress)
    if preflight:return emit(preflightPassed=True,productionChanged=False)
    try:
        for service in ('backend','web'):
            if progress.get(service,{}).get('kind')!='new':
                verify_runtime(manifest,plan,progress);switch(manifest,plan,progress,service,'new')
        verify_runtime(manifest,plan,progress,final=True);public_checks(plan,progress)
        save('deployed.json',{'deployed':True,'atMs':int(time.time()*1000),'services':list(BASES)})
        emit(deployed=True,components=2,nonTargetsUnchanged=True,financialAnchorMs=FINANCIAL_ANCHOR_MS)
    except Exception as exc:
        # Drift and unavailable/busy gates never authorize automatic overwrite.
        if isinstance(exc,GuardError) and str(exc)!='target_health_failed':raise
        restored=False
        try:rollback();restored=True
        except Exception:pass
        save('failed-cutover.json',{'failed':True,'rollbackSucceeded':restored})
        raise GuardError('cutover_failed_rollback_'+('succeeded' if restored else 'needs_attention')) from None


@contextmanager
def release_lock():
    with (ROOT/'release.lock').open('a') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise GuardError('another_release_action_is_running') from None
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def main():
    os.umask(0o077);bind_primitives()
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',nargs='?',default='preflight',choices=('prepare','preflight','deploy','verify','rollback'))
    action=parser.parse_args().action
    try:
        require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve()==ROOT, 'private_release_directory_missing')
        with release_lock():
            {'prepare':prepare,'preflight':lambda:deploy(preflight=True),'deploy':deploy,'verify':verify,'rollback':rollback}[action]()
    except Exception as exc:
        reason=str(exc) if isinstance(exc,GuardError) and re.fullmatch('[a-z0-9_]+',str(exc)) else 'release_operation_failed_private_diagnostics_only'
        emit(ok=False,reason=reason);raise SystemExit(75 if reason=='protected_user_work_cutover_deferred' else 1) from None


bind_primitives()
if __name__=='__main__':main()
