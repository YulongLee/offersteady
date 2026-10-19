## ADDED Requirements

### Requirement: Bound Global question preparation while preserving prompt preparation
Global ordinary interview question prefetch SHALL use the approved leading/latest/final scheduling contract: immediate eligible leading work, one latest pending item per owner/session/question, a 350ms quiet window, a 1500ms maximum wait, a 10s pending TTL, at most 256 tracked keys and two global workers. Final SHALL be immediately eligible, with an idle worker permitted to bypass a running obsolete partial for the same key while global and per-key running work remain at most two. Ordinary partial work SHALL remain single-flight per key.

#### Scenario: Partial updates burst and final arrives
- **WHEN** many stable partial revisions extend one Global question and a newer final arrives while the leading retrieval is blocked
- **THEN** intermediate pending revisions are replaced, final can use the idle second worker without waiting for the old partial, and no extra worker or unbounded pending queue is created

#### Scenario: Final text is unchanged or older partial arrives late
- **WHEN** final has the same text as the previous stable partial, or an older partial observer executes after final
- **THEN** final revision/finality still reaches scheduling and the late partial cannot overwrite final stable state

### Requirement: Global prepared evidence matches current identity and materials
Prepared evidence SHALL require owner/session, question identity/revision, normalized complete question text and the current material fingerprint to match. Fingerprints SHALL cover selection identity and bound document version, readiness/index state, activity and collection. Cache and generation state SHALL be bounded to at most 128 question keys with a 60s prepared-result TTL. Equivalent in-flight work SHALL avoid duplicate retrieval; failed, expired or stale work SHALL NOT create valid reusable evidence. Source evidence SHALL remain distinct from model inference and generated suggestions.

#### Scenario: Document changes without selection revision change
- **WHEN** a Global bound document is reprocessed, deactivated, moved to another collection or loses readiness while selection revision remains equal
- **THEN** older prepared evidence is rejected and cannot be represented as current source material

#### Scenario: Identity, complete text or generation differs
- **WHEN** owner/session differs, a partial is only a substring of final, or a slow older material generation finishes after a new one
- **THEN** the incompatible result cannot be reused or overwrite the newer valid cache entry

### Requirement: Cleanup and clicks retain existing Global realtime behavior
Cleanup/reset/shutdown SHALL revoke queued and running prefetch tokens so old observers/results cannot recreate cleared state or re-enter a new generation. External operations SHALL run outside scheduling/cache locks; synchronous external IO SHALL NOT be force terminated, and unrelated cold persistence/usage work SHALL NOT be cancelled. Explicit quick answer startup SHALL reuse its existing authorized session snapshot without an additional session read or wait for prefetch, with the existing fallback and independent detailed retrieval preserved.

#### Scenario: Cleanup races an observer or cache commit
- **WHEN** session cleanup/reset overlaps a delayed observer, result commit or cache hit
- **THEN** stale work cannot recreate state or return revoked evidence, and unaffected realtime/usage operations keep their contract

#### Scenario: User clicks while both workers are slow
- **WHEN** a Global user explicitly starts an answer while prefetch is blocked or delayed
- **THEN** quick startup does not await preparation or add a session query, and detailed retrieval still reads authoritative current materials

### Requirement: Global product contracts remain isolated
The change SHALL preserve Global independent membership/UTC quotas and absence of CN point-wallet/60-minute flat-billing rules; language, model routing, Prompt/TTS, Creem, published heartbeat/ACK optimizations, ordinary/mock isolation and the existing disabled mock-interview feature flag SHALL remain unchanged. Synthetic verification SHALL NOT activate production features or call real user/provider workflows.

#### Scenario: Regional regression and runtime config inspection
- **WHEN** the actual Global source candidate is tested with isolated synthetic fixtures and its effective production config is compared with the baseline
- **THEN** Global eligibility/quota and realtime behavior pass their prior contracts, mock enabled remains false, and no CN commercial behavior or language/model/Prompt change is introduced
