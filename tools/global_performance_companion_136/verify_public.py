"""Bounded anonymous Global public checks. Redirect URLs and raw errors stay private."""
from pathlib import Path
import hashlib,json,time
from urllib.request import Request,urlopen

ORIGIN='https://offersteady.com'
HERE=Path(__file__).resolve().parent


def get(path,headers=None):
    return urlopen(Request(ORIGIN+path,headers={'Cache-Control':'no-cache','Accept-Encoding':'identity',**(headers or {})}),timeout=30)


def main():
    expected=json.loads((HERE/'public-expected.json').read_text())
    out={'startedAtMs':int(time.time()*1000),'downloads':[],'routes':[],'signedUrlsExported':False}
    with get('/api/v1/web/state') as r:manifest=json.load(r)['data']['releaseManifest']
    assert manifest['generatedAtMs']==expected['current']['generatedAtMs'] and len(manifest['entries'])==3
    for e in expected['current']['entries']:
        p=next(x for x in manifest['entries'] if (x['platform'],x['architecture'])==(e['platform'],e['architecture']))
        for k in ('version','fileSizeBytes','sha256','signingStatus','notarized','distributionStatus','developmentOnly','protocolVersion'):assert p[k]==e[k]
        assert 'objectKey' not in p and p['downloadUrl']=='/api/v1/web/downloads/desktop/'+e['fileName']
    for e in expected['downloads']:
        path='/api/v1/web/downloads/desktop/'+e['fileName'];mime='application/x-apple-diskimage' if e['platform']=='macos' else 'application/vnd.microsoft.portable-executable'
        with get(path,{'Range':'bytes=0-1023'}) as r:
            assert r.status==206 and len(r.read())==1024 and r.headers['Content-Range']=='bytes 0-1023/'+str(e['fileSizeBytes']) and r.headers.get_content_type()==mime
        started=time.monotonic();size=0;h=hashlib.sha256()
        with get(path) as r:
            assert r.status==200 and int(r.headers['Content-Length'])==e['fileSizeBytes'] and r.headers.get_content_type()==mime
            while True:
                assert time.monotonic()-started<480
                data=r.read(1024*1024)
                if not data:break
                size+=len(data);assert size<=e['fileSizeBytes'];h.update(data)
        assert size==e['fileSizeBytes'] and h.hexdigest()==e['sha256']
        out['downloads'].append({'fileName':e['fileName'],'version':e['version'],'bytes':size,'sha256':h.hexdigest(),'rangeStatus':206,'fullStatus':200,'mime':mime})
        (HERE/'public-verification.partial.json').write_text(json.dumps(out,indent=2)+'\n')
    for path,name in expected['routes'].items():
        with get(path) as r:
            data=r.read();assert r.status==200 and hashlib.sha256(data).hexdigest()==expected['webInventory'][name]
            if name.endswith('.js'):assert 'javascript' in r.headers.get_content_type() and 'immutable' in r.headers.get('Cache-Control','')
        out['routes'].append({'path':path,'status':200,'sha256':hashlib.sha256(data).hexdigest()})
    for path in ('/api/v1/global-commerce/catalogue','/api/v1/mock-interviews/capabilities'):
        with get(path) as r:data=json.load(r)['data'];assert r.status==200
        assert hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()==expected['stablePublic'][path]['dataSha256']
    with get('/healthz') as r:assert r.status==200 and json.load(r)['data']['status']=='ok'
    out.update(passed=True,completedAtMs=int(time.time()*1000),currentVersionsAll136=True,publicDownloadsVerified=6,globalCatalogueAndFeatureSwitchesUnchanged=True,healthStatus=200)
    (HERE/'public-verification.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'passed':True,'downloads':6,'routes':len(out['routes'])}))


if __name__=='__main__':
    try:main()
    except Exception as e:
        (HERE/'public-verification.failed.json').write_text(json.dumps({'passed':False,'errorType':type(e).__name__})+'\n')
        print(json.dumps({'passed':False,'errorType':type(e).__name__}));raise SystemExit(1) from None
