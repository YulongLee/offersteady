import base64,hashlib,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cn200_build_stage',R/'scripts/stage_cn_companion_200_build.py');S=importlib.util.module_from_spec(spec);sys.modules[spec.name]=S;spec.loader.exec_module(S)

def test_payload_freezes_exact_reviewed_inputs():
 with tempfile.TemporaryDirectory() as d:
  root=Path(d);local=root/'local';local.mkdir();(root/'scripts').mkdir()
  files={}
  for n in range(14):
   name=f'support-{n}.py';data=f'synthetic-support-{n}'.encode();(local/name).write_bytes(data);files[name]=hashlib.sha256(data).hexdigest()
  probe=b'synthetic-probe';compose=b'synthetic-compose';build=b'synthetic-builder';web=b'synthetic-web';manifest=b'synthetic-manifest'
  (local/'candidate-probe.py').write_bytes(probe);(local/'compose-hashes.json').write_bytes(compose);(root/'scripts/build_cn_companion_200_candidate.py').write_bytes(build)
  ctx=local/'image-build-context';ctx.mkdir();(ctx/'Dockerfile').write_text('FROM sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43\nCOPY overlay/ /app/\n')
  for name,data in [('apps/backend/app/modules/web.py',web),('apps/backend/app/desktop_release_manifest.json',manifest)]:
   p=ctx/'overlay'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  plan={'supportFiles':files,'candidateProbe':{'scriptSha256':hashlib.sha256(probe).hexdigest(),'resultSha256':None},'candidates':{'backend':{'image':None,'inventory':{'apps/backend/app/modules/web.py':hashlib.sha256(web).hexdigest(),'apps/backend/app/desktop_release_manifest.json':hashlib.sha256(manifest).hexdigest()}}}}
  raw=json.dumps(plan).encode();(local/'input.template.json').write_bytes(raw)
  with patch.object(S,'ROOT',root),patch.object(S,'LOCAL',local),patch.object(S,'PLAN_SHA',hashlib.sha256(raw).hexdigest()),patch.object(S,'BUILD_SHA',hashlib.sha256(build).hexdigest()),patch.object(S,'COMPOSE_SHA',hashlib.sha256(compose).hexdigest()):
   x=S.payload();assert len(x)==21
   assert x['build_cn_companion_200_candidate.py'][1]==0o600
   assert x['image-build-context/Dockerfile'][1]==0o644
   (local/'support-0.py').write_bytes(b'tampered')
   with pytest.raises(S.GuardError,match='support_changed'): S.payload()

def test_staging_requires_explicit_execute():
 with patch.object(sys,'argv',['stage']),pytest.raises(S.GuardError,match='explicit_execute_required'):S.main()

def test_receiver_never_replaces_prior_directory_or_accepts_wrong_bytes():
 with tempfile.TemporaryDirectory() as d:
  target=Path(d).resolve()/'stage'; data=b'synthetic';name='nested/file';item={'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest(),'mode':0o600}; script=S.REMOTE_SCRIPT.replace('/opt/offersteady/releases/20261114-cn-companion-200-1',str(target));payload=json.dumps({'root':str(target),'files':{name:item}}).encode()
  def call():return subprocess.run([sys.executable,'-B','-c',script],input=payload,capture_output=True)
  assert call().returncode==0 and (target/name).read_bytes()==data
  assert call().returncode!=0 and (target/name).read_bytes()==data
  other=Path(d).resolve()/'other';script2=S.REMOTE_SCRIPT.replace('/opt/offersteady/releases/20261114-cn-companion-200-1',str(other));item['sha256']='0'*64
  r=subprocess.run([sys.executable,'-B','-c',script2],input=json.dumps({'root':str(other),'files':{name:item}}).encode(),capture_output=True)
  assert r.returncode!=0 and not (other/name).exists()
