"""Synthetic count-only reproduction; no providers, sockets or product env."""
from pathlib import Path
from collections import Counter
from dataclasses import asdict,replace
import hashlib,json,time
from app.ports.realtime_speech import SessionDesktopBindingRecord
from app.services.cn_realtime_entity_state import CNRealtimeEntityState
from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository

manifest=json.loads(Path('docs/releases/cn-pinned-binding-20261104.1/backend-runtime-manifest.json').read_text())
for name in ('apps/backend/app/services/redis_realtime_speech_repository.py','apps/backend/app/services/cn_realtime_entity_state.py'):
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==manifest[name]
results=[]
for size in (1,1191,10000):
    calls=Counter()
    target=SessionDesktopBindingRecord('synthetic-b','synthetic-s','synthetic-owner','synthetic-device','123456','Synthetic',{},1,1)
    rows=[json.dumps(asdict(replace(target,binding_id='synthetic-history-'+str(i),session_id='synthetic-session-'+str(i),owner_user_id='synthetic-other'))) for i in range(size-1)]+[json.dumps(asdict(target))]
    class FakeRedis:
        def hvals(self,key):calls['HVALS']+=1;return rows
        def hexists(self,key,field):calls['HEXISTS']+=1;return False
    store=object.__new__(CNRealtimeEntityState)
    store.redis=FakeRedis();store.retired='synthetic-retired';store.keys=['synthetic-key']*15
    store.candidates='synthetic-candidates';store.accounts='synthetic-accounts'
    repo=object.__new__(RedisRealtimeSpeechRepository);repo._cn_controls=store
    started=time.perf_counter();values=repo.list_session_desktop_bindings_for_user(user_id='synthetic-owner');elapsed=(time.perf_counter()-started)*1000
    assert len(values)==1
    results.append({'syntheticHistory':size,'redisOperations':dict(calls),'totalRoundTrips':sum(calls.values()),'bindingDecodes':size,'syntheticElapsedMs':round(elapsed,3),'productionLatencyMeasured':False})
result={'actualReleaseSourceUsed':True,'findings':results,'realRedisOrDatabaseOrProviderCalls':0,'productionChanges':0}
Path('artifacts/cn-api-p95-20261104-current-700/user-binding-list-cost.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
