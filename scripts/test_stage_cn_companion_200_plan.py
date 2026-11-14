import base64,hashlib,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
R=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('cn200_plan_stage',R/'scripts/stage_cn_companion_200_plan.py');S=importlib.util.module_from_spec(s);sys.modules[s.name]=S;s.loader.exec_module(S)

@pytest.fixture
def synthetic_payload(tmp_path, monkeypatch):
 probe=json.dumps({'image':S.IMAGE,'passed':True}).encode()
 probe_sha=hashlib.sha256(probe).hexdigest()
 plan=json.dumps({'candidates':{'backend':{'image':S.IMAGE}},'candidateProbe':{'resultSha256':probe_sha}}).encode()
 (tmp_path/'input.json').write_bytes(plan);(tmp_path/'candidate-probe-result.json').write_bytes(probe)
 monkeypatch.setattr(S,'LOCAL',tmp_path)
 monkeypatch.setattr(S,'INPUT_SHA',hashlib.sha256(plan).hexdigest())
 monkeypatch.setattr(S,'PROBE_SHA',probe_sha)
 return {'input.json':plan,'candidate-probe-result.json':probe}

def test_local_payload_accepts_only_matching_plan_and_probe(synthetic_payload):
 assert S.payload()==synthetic_payload
 (S.LOCAL/'candidate-probe-result.json').write_bytes(b'tampered')
 with pytest.raises(S.GuardError,match='local_plan_changed'):S.payload()

def test_stage_requires_explicit_execution():
 with patch.object(sys,'argv',['stage']),pytest.raises(S.GuardError,match='explicit_execute_required'):S.main()

def test_receiver_matches_synthetic_proof_and_refuses_overwrite(synthetic_payload):
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp).resolve();files=S.payload();probe=json.loads(files['candidate-probe-result.json']);(root/'release.lock').write_text('');(root/'candidate-build-result.json').write_text(json.dumps({'serviceSwitched':False,'candidateImage':S.IMAGE,'probe':probe}))
  body={'files':{n:{'data':base64.b64encode(v).decode(),'sha256':hashlib.sha256(v).hexdigest()} for n,v in files.items()}}
  fake="\nsubprocess.check_output=lambda a: json.dumps([{'Id':('fe11497d82c625b47dc7e5ffcd0ed6463d17dda9259e18db18a81d45f9021a94' if a[-1]=='compose-backend-1' else "+repr(S.IMAGE)+"),'Image':'sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43','State':{'Running':True}}]).encode()\n"
  script=S.REMOTE_SCRIPT.replace('/opt/offersteady/releases/20261114-cn-companion-200-1',str(root)).replace('from pathlib import Path','from pathlib import Path'+fake)
  def call(payload):return subprocess.run([sys.executable,'-B','-c',script],input=json.dumps(payload).encode(),capture_output=True)
  assert call(body).returncode==0 and (root/'input.json').read_bytes()==files['input.json']
  assert call(body).returncode!=0 and (root/'input.json').read_bytes()==files['input.json']
