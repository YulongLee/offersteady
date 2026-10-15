## ADDED Requirements

### Requirement: Bind cached evidence to identity and materials
Prepared retrieval SHALL match owner, session, question identity/revision, normalized complete question text and current material fingerprint before reuse. The fingerprint SHALL include selection identity and retrieval-visible bound document version/state/activity/collection, even if selection revision is unchanged. Click lookup SHALL reuse its already-authorized session snapshot without another session query.

#### Scenario: Materials are reprocessed without selection changes
- **WHEN** a document version, readiness/index state, activity or collection changes while binding revision remains equal
- **THEN** old prepared evidence is rejected and cannot be cited as current evidence

#### Scenario: Question or identity differs
- **WHEN** a different owner/session or an extended/changed question asks for a prior prepared entry
- **THEN** the entry is not reused merely because text is a substring or a question ID is repeated

### Requirement: Late and duplicate work cannot poison the cache
Prefetch SHALL validate its scheduling token at safe boundaries, verify materials before committing, and use a distinct generation for same-revision material changes. Equivalent same-revision work SHALL reuse completed/in-flight preparation. Failed, expired or superseded work SHALL NOT create a valid cache entry; cache and generation tracking SHALL be bounded.

#### Scenario: Old materials finish after a newer result
- **WHEN** two same-revision preparations use different materials and the older one finishes last
- **THEN** only the newer valid evidence remains reusable

#### Scenario: Duplicate prefetch or expired work
- **WHEN** identical preparation is submitted twice, or a preparation outlives its valid lifetime
- **THEN** duplicate retrieval is avoided and expired completion cannot resurrect valid evidence

### Requirement: Preserve answer contracts and prove local behavior
The optimization SHALL preserve ordinary/automatic answer order, language/Prompt/model routing, billing/idempotency, transcript delivery, normal lifecycle and mock isolation. Local evidence SHALL use only synthetic data/providers, compare retrieval/read counts and relevant latency/grounding behavior, and include current-runtime-source preservation checks. Production deployment SHALL require explicit user authorization, actual runtime image/source verification, protected-work gates, a minimal backend-only candidate and rollback preparation.

#### Scenario: Warm and immediate answer comparisons
- **WHEN** baseline and candidate receive the same synthetic stable-partial/final/click sequences
- **THEN** admitted work is reported alongside leading/final timing, click non-waiting, cache evidence completeness and current-material references, with no claim of measured production P95 improvement

#### Scenario: Existing routes and protected behavior
- **WHEN** the candidate is tested against the saved actual CN source baseline
- **THEN** unrelated functions/routes, published heartbeat/ACK optimizations, model/Prompt and mock/normal billing behavior remain preserved, and production is unchanged until the user explicitly authorizes release

#### Scenario: User authorizes CN release after local validation
- **WHEN** the user explicitly requests production deployment after the local verification
- **THEN** only the CN Backend is updated from its freshly verified actual image, protected active work prevents restart, unchanged components/configuration remain preserved, and health/source/model checks must pass or the previous image is restored
