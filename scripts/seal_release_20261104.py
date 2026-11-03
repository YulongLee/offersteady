"""Seal verified regional public source snapshots; no network or deployment."""
from pathlib import Path
import hashlib,io,json,shutil,subprocess,tarfile

R=Path(__file__).resolve().parents[1]
E=R/'artifacts/global-realtime-blocking-20261104'
DEST=R/'releases/20261104.1'
sha=lambda b:hashlib.sha256(b).hexdigest()

def archive_source(region,source,inventory):
    folder=DEST/region;folder.mkdir(parents=True,exist_ok=True)
    (folder/'backend-runtime-manifest.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
    with tarfile.open(folder/'backend-runtime.tar.gz','w:gz') as t:
        for name,h in sorted(inventory.items()):
            p=source/name;assert p.is_file() and not p.is_symlink(),name
            data=p.read_bytes();assert sha(data)==h,name
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0
            t.addfile(info,io.BytesIO(data))

def prepare():
    assert not DEST.exists(),'release_already_exists'
    live=json.loads((E/'production-verification.json').read_text())
    cn=json.loads((E/'cn-preservation.json').read_text())
    assert live['backend']['image']==json.loads((E/'backend-candidate.json').read_text())['image'] and live['settingsUnchanged'] and live['nonTargetsUnchanged']
    DEST.mkdir()
    archive_source('global',E/'candidate-initial',live['inventories']['backend'])
    archive_source('cn',R/'artifacts/cn-pinned-binding-local-20261104/candidate',cn['inventories']['backend'])
    old=json.loads((R/'releases/20261102.1/manifest.json').read_text())
    components={}
    for region,observation in (('cn',cn),('global',live)):
        for role in ('backend','material-worker','web'):
            name=region+'-'+role
            if role=='backend':
                archive='releases/20261104.1/'+region+'/backend-runtime.tar.gz'
                inventory='releases/20261104.1/'+region+'/backend-runtime-manifest.json'
            else:
                previous=old['components'][name]
                assert json.loads((R/previous['inventory']).read_text())==observation['inventories'][role],name
                assert previous['image']==observation['components'][role]['image'],name
                archive,inventory=previous['archive'],previous['inventory']
            components[name]={'archive':archive,'inventory':inventory,'count':len(observation['inventories'][role]),'image':observation['components'][role]['image']}
    (DEST/'components.json').write_text(json.dumps(components,indent=2)+'\n')
    tools=DEST/'tools';tools.mkdir()
    for name in ('verify_snapshot.py','restore_snapshot.py','test_snapshot_tools.py'):
        s=(R/'releases/20261102.1/tools'/name).read_text().replace('20261102.1','20261104.1')
        (tools/name).write_text(s)
    for name in ('parity','business','extended'):
        shutil.copytree(E/(name+'-tests'),DEST/'global/tests'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(R/'releases/20261102.1/global/ai-evals',DEST/'global/ai-evals')
    shutil.copytree(R/'releases/20261102.1/global/test-fixtures',DEST/'global/test-fixtures')
    evidence=DEST/'evidence';evidence.mkdir()
    for name in ('production-verification.json','cn-preservation.json','candidate-probe-result.json','post-release-error-summary.json','candidate-manifest.json','allowed-delta.json'):
        shutil.copyfile(E/name,evidence/name)
    # Full synthetic test logs stay local; only aggregate summaries and fixed
    # numeric cost evidence enter the source seal.
    summaries={}
    for name in ('parity','business','extended'):
        v=json.loads((E/(name+'-test-summary.json')).read_text())
        summaries[name]={'passed':v['returncode']==0,'tests':sum(int(x['tests']) for x in v['suites']),
                         'failures':sum(int(x['failures'])+int(x['errors']) for x in v['suites']),
                         'skipped':sum(int(x['skipped']) for x in v['suites'])}
    import xml.etree.ElementTree as ET
    summaries['controller']={k:sum(int(s.get(k,0)) for s in ET.parse(E/'controller-tests.xml').getroot().findall('testsuite')) for k in ('tests','errors','failures','skipped')}
    (evidence/'regression-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    xml=ET.parse(E/'parity-tests.xml').getroot()
    props=[{'name':p.get('name'),'value':json.loads(p.get('value'))} for p in xml.findall('.//property') if p.get('name','').startswith(('pinned_read_history_','twelve_mixed_pollers'))]
    (evidence/'synthetic-scale-cost.json').write_text(json.dumps(props,indent=2)+'\n')
    print(json.dumps({'publicSnapshotsPrepared':True,'components':{n:c['count'] for n,c in components.items()}}))

def manifest():
    # Call after explicit staging and final documentation. Bind staged scope,
    # not ignored files, local notes, installation packages or .env files.
    files=subprocess.check_output(['git','ls-files','-z']).split(b'\0')
    seal={}
    for raw in files:
        if not raw:continue
        n=raw.decode();p=R/n
        if n=='releases/20261104.1/manifest.json' or p.is_symlink() or not p.is_file():continue
        seal[n]=sha(p.read_bytes())
    for p in DEST.rglob('*'):
        if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts and p.suffix!='.pyc':seal[str(p.relative_to(R))]=sha(p.read_bytes())
    value={'version':'20261104.1','branch':'codex/release-20261104-1','tag':'release-20261104.1',
        'parentRelease':'release-20261102.1','applicationSecretsIncluded':False,'rawUserDataIncluded':False,
        'productionChangesByGitSeal':False,'companionVersion':'1.3.6','components':json.loads((DEST/'components.json').read_text()),
        'files':dict(sorted(seal.items())),
        'limitations':'Public exact inputs only. Private environments, image layers and user data remain on servers. Root has unreleased screenshot work; regional runtime archives are the production source of truth.'}
    (DEST/'manifest.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'manifestFiles':len(seal),'version':value['version']}))

if __name__=='__main__':
    import sys
    manifest() if '--manifest' in sys.argv else prepare()
