"""Assemble the approved CN mock delta over a complete fresh public inventory.

No network, Docker, private configuration or production mutation is performed.
The caller must independently enforce live image ownership and idle gates.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE_IMAGE = 'sha256:99822e10e7b516aefe4ad96248f9eea631d90b057cb77b8dd386cff4830516fb'
ACTIVE_HTML = ('index.html', 'guide.html', 'privacy.html', 'terms.html')
MUTABLE = {*ACTIVE_HTML, 'offersteady-build.json'}
spec = importlib.util.spec_from_file_location('reviewed_state_graph', ROOT/'tools/state_read_optimization/build_web_release.py')
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)
sha, load_files, references, reachable, reverse_closure, rewrite = (getattr(graph,n) for n in ('sha','load_files','references','reachable','reverse_closure','rewrite'))

def text_assets(files):
    result = {n:b.decode() for n,b in files.items() if n.startswith('assets/') and n.endswith(('.js','.css')) and not PurePosixPath(n).name.startswith('._')}
    if len({PurePosixPath(n).name for n in result}) != len(result):
        raise ValueError('ambiguous executable/style basename')
    return result

def mapping_for(assets, closure, release):
    if not re.fullmatch(r'cn-mock-\d{8}\.\d+',release):
        raise ValueError('invalid mock release id')
    result={}
    for name in sorted(closure):
        path=PurePosixPath(name)
        match=re.fullmatch(r'(.+)-[A-Za-z0-9_-]+\.(js|css)',path.name)
        if not match: raise ValueError('unsupported active asset name')
        seed=(release+'\0'+name+'\0'+sha(assets[name].encode())).encode()
        result[name]=str(path.with_name(match[1]+'-'+sha(seed)[:8]+'.'+match[2]))
    if len(set(result.values()))!=len(result) or set(result.values()) & assets.keys():
        raise ValueError('immutable asset collision')
    return result

def assemble(original,patched,report,release):
    assets=text_assets(original)
    entries=set().union(*(references(original[n].decode(),assets) for n in ACTIVE_HTML))
    active=reachable(assets,entries)
    changed=set(report['patchedOriginalModules']); added=set(report['addedSourceModules'])
    if set(patched)!=changed|added or not changed<=active or added & original.keys():
        raise ValueError('patch scope is outside active fresh graph')
    selected={n:assets[n] for n in active}; selected.update(patched)
    closure=reverse_closure(selected,changed|added)
    mapping=mapping_for(selected,closure,release)
    if set(mapping.values()) & original.keys(): raise ValueError('new asset overwrites original')
    result=dict(original)
    for old,new in mapping.items(): result[new]=rewrite(selected[old],mapping).encode()
    for name in ACTIVE_HTML: result[name]=rewrite(original[name].decode(),mapping).encode()
    build=json.loads(original['offersteady-build.json'])
    if build.get('appEnv')!='production' or build.get('apiBaseUrl')!='/':
        raise ValueError('nonproduction public runtime configuration')
    build['appVersion']=release
    result['offersteady-build.json']=(json.dumps(build,separators=(',',':'))+'\n').encode()
    modified={n for n in original if result[n]!=original[n]}
    if modified != MUTABLE: raise ValueError('unexpected original mutation set')
    inverse={new:old for old,new in mapping.items()}
    for old,new in mapping.items():
        if rewrite(result[new].decode(),inverse)!=selected[old]: raise ValueError('nonreversible graph rewrite')
    for name in ACTIVE_HTML:
        if rewrite(result[name].decode(),inverse)!=original[name].decode(): raise ValueError('HTML changed beyond references')
    for name,data in original.items():
        if name not in MUTABLE and result[name]!=data: raise ValueError('original immutable bytes changed')
    final=text_assets(result)
    final_entries=set().union(*(references(result[n].decode(),final) for n in ACTIVE_HTML))
    final_active=reachable(final,final_entries)
    if final_active & mapping.keys() or not set(mapping.values())<=final_active:
        raise ValueError('mixed or disconnected runtime generation')
    for token in (b'cn-mock-voice-source.js',b'data-local-preview',b'local-preview-synthetic',b'OfferSteadyLocalPreview/'):
        if any(token in result[n] for n in final_active): raise ValueError('source placeholder or preview leaked')
    for name in mapping.values():
        if name.endswith('.js'):
            check=subprocess.run(['node','--check','--input-type=module'],input=result[name],capture_output=True)
            if check.returncode: raise ValueError('invalid generated module '+name)
    return result,{
        'schemaVersion':1,'releaseId':release,'baseWebImage':BASE_IMAGE,'packageReady':True,
        'liveGateRequired':True,'productionWrites':0,'files':len(result),'originalFiles':len(original),
        'unchangedOriginals':len(original)-len(modified),'inventory':{n:sha(b) for n,b in sorted(result.items())},
        'baselineInventory':{n:sha(b) for n,b in sorted(original.items())},
        'modifiedOriginals':{n:{'before':sha(original[n]),'after':sha(result[n])} for n in sorted(modified)},
        'moduleMapping':mapping,'newAssets':{new:{'from':old,'sha256':sha(result[new])} for old,new in sorted(mapping.items())},
        'newModules':{new:{'from':old,'sha256':sha(result[new])} for old,new in sorted(mapping.items()) if new.endswith('.js')},
        'sourceFiles':report['sourceFiles'],'patchedOriginalModules':report['patchedOriginalModules'],
        'invariants':{'allOriginalImmutableAssetsRetained':True,'seoAndMainCssMediaUnchanged':True,
          'reportAndWordImplementationUnchanged':True,'htmlOnlyResourceReferenceChanges':True,
          'moduleReverseEquivalence':True,'newGraphHasNoOldGeneration':True,'fullSourceAppBundleUsed':False,
          'activeAssetsBefore':len(active),'activeAssetsAfter':len(final_active)},
        'rollbackInventory':{n:sha(b) for n,b in sorted((original|{n:result[n] for n in mapping.values()}).items())},
    }

def build(baseline,baseline_manifest,source_manifest,output,release):
    baseline,output=Path(baseline),Path(output)
    expected=json.loads(Path(baseline_manifest).read_text())
    web=expected['baselines']['web']
    if web['image']!=BASE_IMAGE: raise ValueError('unreviewed base Web image')
    original=load_files(baseline)
    inventory={n:sha(b) for n,b in original.items()}
    recorded={n:v.removeprefix('sha256:') for n,v in web['inventory'].items()}
    if inventory!=recorded or len(original)!=353: raise ValueError('fresh full public inventory drift')
    if output.exists() and any(output.iterdir()): raise ValueError('output must be empty')
    with tempfile.TemporaryDirectory(prefix='cn-mock-web-patch-') as temporary:
        subprocess.run(['node',str(Path(__file__).with_name('build_runtime_patch.mjs')),str(baseline),str(source_manifest),temporary],cwd=ROOT,check=True)
        report=json.loads((Path(temporary)/'patch-report.json').read_text())
        patched={n:(Path(temporary)/n).read_text() for n in report['patchedOriginalModules']+report['addedSourceModules']}
    result,manifest=assemble(original,patched,report,release)
    manifest['nginx']={'changed':False,'inputs':expected['nginxInputs']}
    manifest['freshBaselineManifestSha256']=sha(Path(baseline_manifest).read_bytes())
    manifest['sourceHandoffSha256']=sha(Path(source_manifest).read_bytes())
    for name,data in result.items():
        target=output/'web/html'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report_path=output/'web-patch-report.json';report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    manifest['patchReportSha256']=sha(report_path.read_bytes())
    (output/'web-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'releaseId':release,'files':len(result),'newAssets':len(manifest['newAssets']),
      'modifiedOriginals':sorted(manifest['modifiedOriginals']),'nginxWritten':False}))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',required=True,type=Path);p.add_argument('--baseline-manifest',required=True,type=Path)
    p.add_argument('--source-manifest',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--release-id',default='cn-mock-20261101.1')
    a=p.parse_args();build(a.baseline,a.baseline_manifest,a.source_manifest,a.output,a.release_id)
