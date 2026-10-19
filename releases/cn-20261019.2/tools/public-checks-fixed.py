"""Public route verification and bounded transient readiness; no body diagnostics."""
import json,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

PUBLIC_HTML_ROUTES={'index.html':'/login','guide.html':'/guide','terms.html':'/terms','privacy.html':'/privacy'}


def public_static_route(file):
    if file in PUBLIC_HTML_ROUTES:return PUBLIC_HTML_ROUTES[file]
    if file.startswith('assets/') and '\\' not in file and '..' not in file.split('/'):
        return '/'+file
    raise ValueError('unapproved_public_file_route')


def public_checks(m):
    plan=m.read_json(m.ROOT/'input.json');results=[]
    progress=m.read_json(m.ROOT/'progress.json') if (m.ROOT/'progress.json').exists() else {}
    expected_web=plan['webBefore']|(plan['webFiles'] if progress.get('web',{}).get('kind')=='new' else {})
    def flush():m.save('public-checks.json',{'atMs':int(time.time()*1000),'checks':results})
    def check(path,*,source=None,expected_status=200,expected_sha=None,health=False,no_store=False):
        record={'path':path,'sourceFile':source,'expectedStatus':expected_status,'status':None,'state':'requesting','attempts':[]}
        results.append(record);flush();began=time.monotonic()
        reason='anonymous_optimizer_guard_failed' if expected_status==401 else 'public_route_unavailable'
        for attempt in range(1,4):
            row={'number':attempt,'status':None,'state':'requesting'}
            record['attempts'].append(row);record['state']='requesting';flush();transient=False
            try:
                try:
                    response=urlopen(Request('https://mianshiwen.cn'+path,headers={'Cache-Control':'no-cache'}),timeout=15)
                except HTTPError as error:response=error
                with response:
                    record['status']=row['status']=response.status
                    if response.status!=expected_status:
                        transient=response.status in (502,503)
                        raise m.GuardError(reason)
                    if no_store and response.headers.get('Cache-Control')!='private, no-store':raise m.GuardError(reason)
                    if expected_status==200:
                        data=response.read(4*1024*1024+1)
                        if len(data)>4*1024*1024:raise m.GuardError('public_response_size_exceeded')
                        record['sha256']=m.digest(data)
                        if expected_sha is not None and record['sha256']!=expected_sha:
                            raise m.GuardError('public_static_identity_mismatch')
                        if health and json.loads(data)['data']['status']!='ok':raise m.GuardError('public_health_unavailable')
                record['state']=row['state']='passed';record['elapsedMs']=round((time.monotonic()-began)*1000);flush();return
            except m.GuardError as error:
                row.update(state='failed',reason=str(error),errorType='GuardError')
                record.update(state='retrying' if transient and attempt<3 else 'failed',reason=str(error),errorType='GuardError')
                record['elapsedMs']=round((time.monotonic()-began)*1000);flush()
                if not transient or attempt==3:raise
            except Exception as error:
                transient=isinstance(error,(URLError,TimeoutError))
                error_type=type(error).__name__ if type(error) in (URLError,TimeoutError,OSError,ValueError,KeyError,json.JSONDecodeError) else 'OtherTransportOrDecodeError'
                row.update(state='failed',reason=reason,errorType=error_type)
                record.update(state='retrying' if transient and attempt<3 else 'failed',reason=reason,errorType=error_type)
                record['elapsedMs']=round((time.monotonic()-began)*1000);flush()
                if not transient or attempt==3:raise m.GuardError(reason) from None
            time.sleep(1)
    for path in ('/healthz','/login','/offersteady-build.json','/app/resume-optimizer','/app/mock-interviews','/app/interviews/new','/app/written-exams'):
        source=None if path=='/healthz' else 'offersteady-build.json' if path=='/offersteady-build.json' else 'index.html'
        check(path,source=source,expected_sha=expected_web[source] if source else None,health=path=='/healthz')
    for path in ('/api/v1/resume-optimizer/capabilities','/api/v1/resume-optimizer/jobs/synthetic-invalid/export?format=pdf&expectedRevision=1&factsConfirmed=true'):
        check(path,expected_status=401,no_store=True)
    for file,expected in sorted(plan['webFiles'].items()):
        check(public_static_route(file),source=file,expected_sha=expected)
    return results
