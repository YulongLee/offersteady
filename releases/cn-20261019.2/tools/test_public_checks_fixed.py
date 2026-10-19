from pathlib import Path
import importlib.util,hashlib,json
from types import SimpleNamespace
from urllib.error import HTTPError,URLError
from io import BytesIO
import pytest
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('fixed_public',HERE/'public-checks-fixed.py');v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
class GuardError(RuntimeError):pass
class Response:
 def __init__(self,status=200,data=b'',headers=None):self.status=status;self.data=data;self.headers=headers or {}
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self,limit):return self.data[:limit]
@pytest.fixture
def f(tmp_path,monkeypatch):
 sha=lambda b:hashlib.sha256(b).hexdigest()
 web={'index.html':sha(b'index'),'guide.html':sha(b'guide'),'privacy.html':sha(b'privacy'),'terms.html':sha(b'terms'),'assets/new-12345678.js':sha(b'asset')}
 plan={'webBefore':{'index.html':sha(b'old'),'offersteady-build.json':sha(b'build')},'webFiles':web}
 (tmp_path/'input.json').write_text(json.dumps(plan));(tmp_path/'progress.json').write_text(json.dumps({'web':{'kind':'new'}}))
 logs=[];calls=[]
 def save(name,value):logs.append(json.loads(json.dumps(value)));(tmp_path/name).write_text(json.dumps(value))
 m=SimpleNamespace(ROOT=tmp_path,read_json=lambda p:json.loads(p.read_text()),save=save,digest=sha,GuardError=GuardError)
 def request(req,**kwargs):
  path=req.full_url.removeprefix('https://mianshiwen.cn');calls.append(path)
  if path.startswith('/api/'):return Response(401,headers={'Cache-Control':'private, no-store'})
  data=b'{"data":{"status":"ok"}}' if path=='/healthz' else b'build' if path=='/offersteady-build.json' else {'/guide':b'guide','/privacy':b'privacy','/terms':b'terms','/assets/new-12345678.js':b'asset'}.get(path,b'index')
  return Response(data=data)
 monkeypatch.setattr(v,'urlopen',request)
 monkeypatch.setattr(v.time,'sleep',lambda *a:None)
 return m,request,calls,logs

def test_html_files_use_existing_public_routes_and_assets_use_exact_url(f):
 m,_,calls,_=f;result=v.public_checks(m)
 assert len(result)==14 and all(r['state']=='passed' for r in result)
 assert calls[-5:]==['/assets/new-12345678.js','/guide','/login','/privacy','/terms']
 assert not any(path.endswith('.html') for path in calls)

@pytest.mark.parametrize('file,path',[('index.html','/login'),('guide.html','/guide'),('terms.html','/terms'),('privacy.html','/privacy'),('assets/new-12345678.js','/assets/new-12345678.js')])
def test_exact_mapping(file,path):assert v.public_static_route(file)==path

@pytest.mark.parametrize('file',['nginx.conf','../private','assets/../private','assets/\\private'])
def test_unapproved_route_not_requested(file):
 with pytest.raises(ValueError):v.public_static_route(file)

@pytest.mark.parametrize('kind',['404','502','timeout','urlerror','hash','json'])
def test_failure_has_path_status_and_fixed_error_but_no_private_body(f,monkeypatch,kind):
 m,original,calls,logs=f
 def fail(req,**kwargs):
  if kind=='404':raise HTTPError(req.full_url,404,'private-body-secret',{},BytesIO(b'private-body-secret'))
  if kind=='502':return Response(502,b'private-body-secret')
  if kind=='timeout':raise TimeoutError('private-body-secret')
  if kind=='urlerror':raise URLError('private-body-secret')
  return Response(data=b'wrong' if kind=='hash' else b'private-body-secret')
 if kind=='hash':
  def custom(req,**kwargs):return fail(req,**kwargs) if req.full_url.endswith('/login') else original(req,**kwargs)
  monkeypatch.setattr(v,'urlopen',custom)
 else:monkeypatch.setattr(v,'urlopen',fail)
 with pytest.raises(GuardError):v.public_checks(m)
 record=logs[-1]['checks'][-1]
 assert record['path']==('/login' if kind=='hash' else '/healthz') and record['state']=='failed'
 assert record['status']==(404 if kind=='404' else 502 if kind=='502' else 200 if kind in ('hash','json') else None)
 assert 'private-body-secret' not in json.dumps(logs)
 assert any(x['checks'][-1]['state']=='requesting' for x in logs)


def test_expected_anonymous_status_does_not_read_response_body(f,monkeypatch):
 m,original,_,_=f
 def custom(req,**kwargs):
  if '/api/' in req.full_url:
   response=Response(401,headers={'Cache-Control':'private, no-store'})
   response.read=lambda *a:pytest.fail('private error body must not be read')
   return response
  return original(req,**kwargs)
 monkeypatch.setattr(v,'urlopen',custom);v.public_checks(m)


@pytest.mark.parametrize('status',[404,403,500])
def test_permanent_http_errors_never_retry(f,monkeypatch,status):
 m,_,calls,logs=f
 def fail(req,**kw):calls.append(req.full_url);return Response(status,b'private-secret')
 monkeypatch.setattr(v,'urlopen',fail)
 with pytest.raises(GuardError):v.public_checks(m)
 assert len(calls)==1 and len(logs[-1]['checks'][-1]['attempts'])==1


@pytest.mark.parametrize('status',[502,503,'transport'])
def test_transient_readiness_is_bounded_then_requires_correct_bytes(f,monkeypatch,status):
 m,original,calls,logs=f;count=0
 def respond(req,**kw):
  nonlocal count
  if req.full_url.endswith('/healthz'):
   count+=1
   if count<3:
    if status=='transport':raise URLError('private-secret')
    return Response(status,b'private-secret')
  return original(req,**kw)
 monkeypatch.setattr(v,'urlopen',respond);v.public_checks(m)
 first=logs[-1]['checks'][0]
 assert count==3 and first['state']=='passed' and len(first['attempts'])==3
 assert all(r['state']=='failed' for r in first['attempts'][:2]) and first['attempts'][-1]['status']==200
 assert 'private-secret' not in json.dumps(logs)


def test_three_unready_observations_stop_without_a_fourth(f,monkeypatch):
 m,_,calls,logs=f
 def fail(req,**kw):calls.append(req.full_url);return Response(503)
 monkeypatch.setattr(v,'urlopen',fail)
 with pytest.raises(GuardError):v.public_checks(m)
 assert len(calls)==3 and logs[-1]['checks'][-1]['state']=='failed'


def test_successful_retry_still_requires_full_expected_hash(f,monkeypatch):
 m,original,calls,logs=f;count=0
 def fail(req,**kw):
  nonlocal count
  if req.full_url.endswith('/login'):
   count+=1;return Response(503) if count==1 else Response(data=b'wrong-hash')
  return original(req,**kw)
 monkeypatch.setattr(v,'urlopen',fail)
 with pytest.raises(GuardError,match='public_static_identity_mismatch'):v.public_checks(m)
 assert count==2 and len(logs[-1]['checks'][-1]['attempts'])==2


def test_original_direct_html_404s_are_not_requested_and_public_routes_match_hashes(f,monkeypatch):
 m,original,calls,logs=f
 def router(req,**kw):
  if req.full_url.endswith('.html'):raise HTTPError(req.full_url,404,'not public',{},BytesIO())
  return original(req,**kw)
 monkeypatch.setattr(v,'urlopen',router)
 result=v.public_checks(m)
 assert len(result)==14 and all(r['state']=='passed' for r in result)
 assert {'/guide','/login','/privacy','/terms'}<=set(calls)
 assert not any(p.endswith('.html') for p in calls)
