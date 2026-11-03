"""CN runtime control entities. Atomic Redis writes; no process-wide IO lock.

The old snapshot is a one-time read-only seed, not a second writer protocol.
Retirement/seed metadata outlives every legacy value it can otherwise revive.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, replace

from app.ports.realtime_speech import AccountDesktopDeviceRecord, QuestionCandidateRecord, SessionDesktopBindingRecord, WebSessionHeartbeatRecord, RealtimePublisherRecord, RealtimeFrameReceiptRecord, TranscriptSegmentRecord, RealtimeEvent, AsrUsageReport


_SCRIPT = r'''
local op, ttl = ARGV[1], tonumber(ARGV[2])
local C,A,B,D,I,R,V,M,O = unpack(KEYS)
local base = ARGV[3]
local function keep(k)
  local lifetime = (k == R or k == M or k == O) and tonumber(ARGV[4]) or ttl
  if lifetime < 0 then redis.call('PERSIST', k) else
    local current = redis.call('TTL', k)
    redis.call('EXPIRE', k, math.max(lifetime, current))
  end
end
local function bump(sid)
  local rows=redis.call('XREVRANGE','offersteady:realtime:events:' .. sid,'+','-','COUNT',1)
  if #rows > 0 then
    local fields=rows[1][2]
    for i=1,#fields,2 do
      if fields[i] == 'cursor' and tonumber(fields[i+1]) > tonumber(redis.call('HGET',V,sid) or '0') then
        redis.call('HSET',V,sid,fields[i+1])
      end
    end
  end
  local version = redis.call('HINCRBY', V, sid, 1); keep(V); return version
end
local function retired(sid) return redis.call('HEXISTS', R, sid) == 1 end
local function owner(sid, uid)
  local current = redis.call('HGET', O, sid)
  if current and current ~= uid then return false end
  redis.call('HSETNX', O, sid, uid); keep(O); return true
end
local function encode(x) return cjson.encode(x) end
local function candidate_record(raw)
  local value=cjson.decode(raw)
  if value.cn_candidate_schema == 1 then
    local n=cjson.decode(value.record_json)
    for k,v in pairs(value.overrides) do n[k]=v end
    return n
  end
  return value
end
local function binding_record(raw)
  local value=cjson.decode(raw)
  if value.cn_binding_schema == 1 then
    local n=cjson.decode(value.record_json)
    for k,v in pairs(value.overrides) do n[k]=v end
    return n
  end
  return value
end
local function binding_raw(raw, status)
  local value=cjson.decode(raw)
  if value.cn_binding_schema == 1 then
    value.overrides.status=status
    return encode(value)
  end
  return encode({cn_binding_schema=1,record_json=raw,overrides={status=status}})
end
if op ~= 'seed' and op ~= 'binding_lookup' and op ~= 'pinned_binding_lookup' then
  -- Retain the previous snapshot's shared runtime lifetime without copying its
  -- body. Freshness/permissions remain in their original record timestamps.
  for _, k in ipairs({C,A,B,D,I,R,M,O}) do keep(k) end
end
local function newer_binding(n, p)
  if n.device_id == p.device_id and n.binding_generation ~= p.binding_generation then
    return n.binding_generation > p.binding_generation
  end
  if n.bound_at_ms ~= p.bound_at_ms then return n.bound_at_ms > p.bound_at_ms end
  if n.status ~= p.status then return n.status == 'stale' end
  return n.last_seen_at_ms >= p.last_seen_at_ms
end
local function index_binding(n, raw)
  for _, item in ipairs({{D,n.device_id .. '|' .. n.manual_code},{I,n.manual_code}}) do
    local old = redis.call('HGET', item[1], item[2])
    local p=old and binding_record(old)
    local newer=not p or n.bound_at_ms > p.bound_at_ms or
      (n.bound_at_ms == p.bound_at_ms and (n.session_id > p.session_id or
       (n.session_id == p.session_id and newer_binding(n,p))))
    if newer then redis.call('HSET',item[1],item[2],raw) end
    keep(item[1])
  end
end
if op == 'pinned_binding_lookup' then
  local sid, bid, device, code = ARGV[5], ARGV[6], ARGV[7], ARGV[8]
  local uid = redis.call('HGET',O,sid)
  if not uid then return {'',0} end
  local raw = redis.call('HGET',B,uid .. '|' .. sid)
  if not raw then return {'',0} end
  local n = binding_record(raw)
  if n.owner_user_id ~= uid or n.session_id ~= sid then return {'',-1} end
  if n.binding_id ~= bid or n.device_id ~= device or n.manual_code ~= code then return {'',0} end
  -- Keep the original bytes: cjson re-encoding can change arrays/numbers.
  -- This lookup deliberately does not renew TTL, seed or repair indexes.
  return {raw,retired(sid) and 1 or 0}
end
if op == 'binding_lookup' then
  local device, code = ARGV[5], ARGV[6]
  local key=device ~= '' and D or I
  local field=device ~= '' and device .. '|' .. code or code
  local indexed=redis.call('HGET',key,field)
  if indexed then
    local p=binding_record(indexed)
    local current=redis.call('HGET',B,p.owner_user_id .. '|' .. p.session_id)
    if current then
      local n=binding_record(current)
      if n.manual_code == code and (device == '' or n.device_id == device) then
        return {current, retired(n.session_id) and 1 or 0}
      end
    end
  end
  -- Repair only a missing/invalid index. Subsequent matching reads are O(1),
  -- and all new writers atomically update these same indexes.
  local best, raw_best = nil, nil
  for _, raw in ipairs(redis.call('HVALS',B)) do
    local n=binding_record(raw)
    if n.manual_code == code and (device == '' or n.device_id == device) and
      (not best or n.bound_at_ms > best.bound_at_ms or (n.bound_at_ms == best.bound_at_ms and n.session_id > best.session_id)) then
      best=n; raw_best=raw
    end
  end
  if raw_best then
    index_binding(best,raw_best)
    return {raw_best,retired(best.session_id) and 1 or 0}
  end
  return {'',0}
end
if op == 'seed' then
  if redis.call('EXISTS',M) == 1 then return 0 end
  local payload, count = cjson.decode(ARGV[5]), 0
  for _, raw in ipairs(redis.call('HVALS',B)) do
    local n=binding_record(raw)
    if not owner(n.session_id,n.owner_user_id) then return redis.error_reply('cn_runtime_entity_identity_mismatch') end
    index_binding(n,raw)
  end
  for sid,version in pairs(payload.activity) do
    if not retired(sid) and version > tonumber(redis.call('HGET',V,sid) or '0') then redis.call('HSET',V,sid,version) end
  end
  keep(V)
  for _, raw in ipairs(payload.candidates) do
    local n = cjson.decode(raw)
    if not retired(n.session_id) and owner(n.session_id,n.owner_user_id) then
      count = count + redis.call('HSETNX',C,n.candidate_id,raw)
      local current = redis.call('HGET',C,n.candidate_id)
      local p = candidate_record(current)
      if p.session_id == n.session_id and p.owner_user_id == n.owner_user_id then
        redis.call('HSET',base .. ':candidates:' .. p.session_id,p.candidate_id,current)
        keep(base .. ':candidates:' .. p.session_id)
      end
    end
  end
  for _, raw in ipairs(payload.accounts) do
    local n = cjson.decode(raw)
    count = count + redis.call('HSETNX',A,n.owner_user_id .. '|' .. n.device_id,raw)
  end
  for _, raw in ipairs(payload.bindings) do
    local n = cjson.decode(raw)
    if owner(n.session_id,n.owner_user_id) then
      if retired(n.session_id) then n.status='stale'; raw=binding_raw(raw,'stale') end
      count = count + redis.call('HSETNX',B,n.owner_user_id .. '|' .. n.session_id,raw)
      local current = redis.call('HGET',B,n.owner_user_id .. '|' .. n.session_id)
      index_binding(binding_record(current),current)
    end
  end
  for _, k in ipairs({C,A,B,R}) do keep(k) end
  redis.call('SET',M,'1'); keep(M); return count
end
if op == 'account' then
  local n = cjson.decode(ARGV[5]); local field=n.owner_user_id .. '|' .. n.device_id
  local old = redis.call('HGET',A,field)
  if old then
    local p=cjson.decode(old)
    if p.last_used_at_ms > n.last_used_at_ms then return {1,old,0} end
    n.linked_at_ms=math.min(p.linked_at_ms,n.linked_at_ms)
  end
  local raw=encode(n); redis.call('HSET',A,field,raw); keep(A); return {1,raw,0}
end
if op == 'candidate' then
  local n=cjson.decode(ARGV[5]); local old=redis.call('HGET',C,n.candidate_id)
  if retired(n.session_id) then return {0,'',0} end
  if old then
    local p=candidate_record(old)
    if p.session_id ~= n.session_id or p.owner_user_id ~= n.owner_user_id then return {-1,'',0} end
    if ARGV[6] == 'cas' then
      -- Compare decoded records, since legacy JSON and cjson key orders differ.
      local e=cjson.decode(ARGV[7])
      local function equal(x,y)
        if type(x) ~= type(y) then return false end
        if type(x) ~= 'table' then return x == y end
        for k,v in pairs(x) do if not equal(v,y[k]) then return false end end
        for k,_ in pairs(y) do if x[k] == nil then return false end end
        return true
      end
      if not equal(p,e) then return {0,old,0} end
      n.updated_at_ms=math.max(p.updated_at_ms,n.updated_at_ms)
    elseif p.updated_at_ms > n.updated_at_ms then return {1,old,0}
    else
      if p.state ~= 'needs-confirmation' and n.state == 'needs-confirmation' then n.state=p.state; n.reason=p.reason end
      if p.answer_task_id ~= cjson.null and p.answer_task_id ~= nil then n.answer_task_id=p.answer_task_id end
    end
  elseif ARGV[6] == 'cas' then return {0,'',0} end
  if not owner(n.session_id,n.owner_user_id) then return {-1,'',0} end
  -- Keep the exact Python JSON for confidence precision and [] shape. Only
  -- primitive merge fields go through cjson encoding, never the record body.
  local raw=encode({cn_candidate_schema=1,record_json=ARGV[5],overrides={
    state=n.state,reason=n.reason,answer_task_id=n.answer_task_id,updated_at_ms=n.updated_at_ms}})
  redis.call('HSET',C,n.candidate_id,raw)
  local sk=base .. ':candidates:' .. n.session_id
  redis.call('HSET',sk,n.candidate_id,raw); keep(C); keep(sk)
  return {1,raw,bump(n.session_id)}
end
if op == 'binding' then
  local n=cjson.decode(ARGV[5]); local field=n.owner_user_id .. '|' .. n.session_id
  if not owner(n.session_id,n.owner_user_id) then return {-1,'',0} end
  local old=redis.call('HGET',B,field)
  if retired(n.session_id) then
    if old then return {1,old,0} end
    n.status='stale'
  end
  if old and not newer_binding(n,binding_record(old)) then return {1,old,0} end
  local raw=binding_raw(ARGV[5],n.status); redis.call('HSET',B,field,raw); keep(B); index_binding(n,raw)
  return {1,raw,bump(n.session_id)}
end
if op == 'clear' then
  local sid=ARGV[5]
  redis.call('HSET',R,sid,'1'); keep(R)
  local sk=base .. ':candidates:' .. sid
  local ids=redis.call('HKEYS',sk)
  if #ids == 0 then
    local rows=redis.call('HGETALL',C)
    for i=1,#rows,2 do
      if candidate_record(rows[i+1]).session_id == sid then table.insert(ids,rows[i]) end
    end
  end
  for _, id in ipairs(ids) do redis.call('HDEL',C,id) end
  redis.call('DEL',sk)
  local uid=redis.call('HGET',O,sid)
  if uid then
    local field=uid .. '|' .. sid; local raw=redis.call('HGET',B,field)
    if raw then
      local n=binding_record(raw); n.status='stale'; raw=binding_raw(raw,'stale')
      redis.call('HSET',B,field,raw)
      index_binding(n,raw)
    end
  end
  return #ids
end
if op == 'publisher' or op == 'receipt' or op == 'transcript' or op == 'event' then
  local n=cjson.decode(ARGV[5]); local raw=ARGV[5]
  if retired(n.session_id) then return {0,'',0} end
  if not owner(n.session_id,n.owner_user_id) then return {-1,'',0} end
  keep(base .. ':candidates:' .. n.session_id)
  if op == 'publisher' then
    redis.call('HSET',KEYS[13],n.publisher_id,raw)
    redis.call('HSET',KEYS[14],n.token,n.publisher_id)
    keep(KEYS[13]); keep(KEYS[14]); return {1,raw,0}
  elseif op == 'receipt' then
    redis.call('HSET',KEYS[15],n.session_id .. ':' .. n.source_kind .. ':' .. n.source_id,raw)
    keep(KEYS[15]); return {1,raw,0}
  elseif op == 'transcript' then
    redis.call('HSET',KEYS[12],n.session_id .. ':' .. n.segment_id,raw)
    keep(KEYS[12]); return {1,raw,bump(n.session_id)}
  else
    local version=bump(n.session_id)
    local stream='offersteady:realtime:events:' .. n.session_id
    local index='offersteady:realtime:event-cursors:' .. n.session_id
    local latest='offersteady:realtime:latest-events:' .. n.session_id
    local retention=tonumber(ARGV[6])
    local id=redis.call('XADD',stream,'MAXLEN','~',retention,'*','cursor',version,'event',raw)
    redis.call('ZADD',index,version,id)
    redis.call('ZREMRANGEBYRANK',index,0,-(retention+1))
    redis.call('HSET',latest,n.kind,raw)
    keep(stream); keep(index); keep(latest)
    return {1,raw,version}
  end
end
if op == 'heartbeat' or op == 'claim' then
  local n=cjson.decode(ARGV[5])
  if retired(n.session_id) then return {0,'',0} end
  keep(base .. ':candidates:' .. n.session_id)
  local H,U=KEYS[10],KEYS[11]
  if op == 'claim' then
    local raw=redis.call('HGET',U,n.owner_user_id); local generation=1
    if raw then
      local p=cjson.decode(raw)
      if not retired(p.session_id) then
        generation=p.lease_generation + 1
        if p.session_id == n.session_id and p.page_instance_id == n.page_instance_id then generation=p.lease_generation end
      end
    end
    n.lease_generation=generation
  end
  local raw=encode(n); redis.call('HSET',H,n.owner_user_id .. '|' .. n.session_id,raw)
  if n.page == 'live' and n.page_instance_id ~= cjson.null and n.page_instance_id and n.page_instance_id ~= '' then redis.call('HSET',U,n.owner_user_id,raw) end
  keep(H); keep(U); return {1,raw,0}
end
return redis.error_reply('unsupported_cn_entity_operation')
'''


class CNRealtimeEntityState:
    def __init__(self, redis, *, base: str, ttl: int, retention: int = 1000):
        self.redis, self.base, self.ttl = redis, base, ttl
        self.retention = retention
        # The compatible old snapshot has no writers in this CN protocol. Its
        # original remaining lifetime only decreases; do not add a network TTL
        # roundtrip to every audio receipt or event. Nonexpiring legacy requires
        # nonexpiring content-free compatibility metadata.
        legacy_sources = (base, f"{base}:entities:bindings:v1")
        pipeline = self.redis.pipeline()
        for key in legacy_sources:
            pipeline.pttl(key)
        legacy_lifetimes = pipeline.execute()
        self._legacy_deadline = (None if -1 in legacy_lifetimes else
                                 time.monotonic() + max(0, *legacy_lifetimes) / 1000)
        self._script = self.redis.register_script(_SCRIPT)
        self.candidates = f"{base}:entities:candidates:v1"
        self.accounts = f"{base}:entities:account-devices:v1"
        self.retired = f"{base}:entities:retired-sessions:v1"
        self.legacy_bindings = f"{base}:entities:bindings:v1"
        self.keys = [self.candidates, self.accounts, f"{base}:entities:cn-bindings:v1",
                     f"{base}:indexes:cn-binding-devices:v1", f"{base}:indexes:cn-binding-codes:v1",
                     self.retired, f"{base}:activity", f"{base}:entities:control-seeded:v1",
                     f"{base}:entities:session-owners:v1", f"{base}:entities:web-heartbeats:v1",
                     f"{base}:indexes:active-web-users:v1", f"{base}:transcripts",
                     f"{base}:publishers", f"{base}:publisher-tokens", f"{base}:receipts"]

    @staticmethod
    def encode(record):
        return json.dumps(asdict(record), ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    def call(self, op, *args):
        ttl = -1 if self._legacy_deadline is None else max(self.ttl, math.ceil(self._legacy_deadline - time.monotonic()))
        # redis-py's script helper uses EVALSHA; NOSCRIPT loads an unexecuted
        # script and then executes once. Other failures propagate without replay.
        return self._script(keys=self.keys, args=[op, self.ttl, self.base, ttl, *args])

    def is_retired(self, session_id):
        return bool(self.redis.hexists(self.retired, session_id))

    def seed(self, *, candidates, accounts, bindings, activity):
        payload = {"candidates": [self.encode(x) for x in candidates],
                   "accounts": [self.encode(x) for x in accounts],
                   "bindings": [self.encode(x) for x in bindings], "activity": activity}
        return int(self.call("seed", json.dumps(payload)))

    def save(self, op, record, *, expected=None):
        result = self.call(op, self.encode(record), str(self.retention) if op == "event" else "cas" if expected is not None else "save",
                           self.encode(expected) if expected is not None else "")
        if int(result[0]) < 0:
            raise ValueError("cn_runtime_entity_identity_mismatch")
        if not int(result[0]):
            return None, 0
        cls = {"candidate": QuestionCandidateRecord, "binding": SessionDesktopBindingRecord,
               "account": AccountDesktopDeviceRecord, "heartbeat": WebSessionHeartbeatRecord,
               "claim": WebSessionHeartbeatRecord, "publisher": RealtimePublisherRecord,
               "receipt": RealtimeFrameReceiptRecord, "transcript": TranscriptSegmentRecord,
               "event": RealtimeEvent}[op]
        stored = self.decode(cls, result[1])
        if op == "binding" and self.is_retired(stored.session_id):
            stored = replace(stored, status="stale")
        return stored, int(result[2])

    @staticmethod
    def decode(cls, raw):
        payload = json.loads(raw)
        if cls is QuestionCandidateRecord and payload.get("cn_candidate_schema") == 1:
            original = json.loads(payload["record_json"])
            original.update(payload["overrides"])
            payload = original
        if cls is SessionDesktopBindingRecord and payload.get("cn_binding_schema") == 1:
            original = json.loads(payload["record_json"])
            original.update(payload["overrides"])
            payload = original
        if cls is QuestionCandidateRecord and payload.get("source_segment_ids") == {}:
            payload["source_segment_ids"] = []
        if cls is TranscriptSegmentRecord and isinstance(payload.get("usage"), dict):
            payload["usage"] = AsrUsageReport(**payload["usage"])
        return cls(**payload)

    def candidate(self, candidate_id):
        raw = self.redis.hget(self.candidates, candidate_id)
        record = self.decode(QuestionCandidateRecord, raw) if raw else None
        if record is None or self.is_retired(record.session_id):
            return None
        scoped = self.redis.hget(f"{self.base}:candidates:{record.session_id}", candidate_id)
        return self.decode(QuestionCandidateRecord, scoped) if scoped else None

    def session_candidates(self, session_id):
        if self.is_retired(session_id):
            return []
        records = [self.decode(QuestionCandidateRecord, raw) for raw in self.redis.hvals(f"{self.base}:candidates:{session_id}")]
        return sorted(records, key=lambda x: x.created_at_ms)

    def all_records(self, kind):
        key, cls = {"candidate": (self.candidates, QuestionCandidateRecord),
                    "account": (self.accounts, AccountDesktopDeviceRecord),
                    "binding": (self.keys[2], SessionDesktopBindingRecord)}[kind]
        records = [self.decode(cls, raw) for raw in self.redis.hvals(key)]
        if kind == "candidate":
            return [x for x in records if not self.is_retired(x.session_id)]
        if kind == "binding":
            return [replace(x, status="stale") if self.is_retired(x.session_id) else x for x in records]
        return records

    def latest_binding(self, *, manual_code, device_id=None):
        raw, is_retired = self.call("binding_lookup", device_id or "", manual_code)
        if not raw:
            return None
        record = self.decode(SessionDesktopBindingRecord, raw)
        return replace(record, status="stale") if is_retired else record

    def pinned_binding(self, *, device_id, manual_code, session_id, binding_id):
        raw, is_retired = self.call("pinned_binding_lookup", session_id, binding_id, device_id, manual_code)
        if int(is_retired) < 0:
            raise ValueError("cn_runtime_entity_identity_mismatch")
        if not raw:
            return None
        record = self.decode(SessionDesktopBindingRecord, raw)
        return replace(record, status="stale") if is_retired else record
