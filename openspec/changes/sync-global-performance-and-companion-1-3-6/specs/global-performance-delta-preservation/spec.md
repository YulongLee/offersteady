## ADDED Requirements

### Requirement: Performance work is based on reviewed actual Global differences
The change SHALL inventory actual running Global component images, complete inputs, effective configuration and API contracts before selecting performance deltas. Backend and Web implementation SHALL remain scopeReviewPending until a concrete missing-behavior and file/symbol allowlist has been recorded and reviewed. Already present optimizations SHALL be preserved without reapplication, and CN or old current-directory files MUST NOT replace the actual Global baseline wholesale.

#### Scenario: Desktop is ready while server differences are unknown
- **WHEN** approved Global Desktop1.3.6 adaptation can proceed but Backend/Web missing optimizations have not been verified
- **THEN** Desktop implementation and packaging may proceed while server/Web activity remains read-only inventory until its separate allowlist review passes

#### Scenario: Global already contains an optimization
- **WHEN** actual Global source and contract checks confirm the behavior is already deployed
- **THEN** the release records it as preserved and does not overwrite it from another stream

### Requirement: Shared read optimizations preserve authoritative behavior
Reviewed authentication, state, heartbeat and control read reductions SHALL retain existing Global authorization, authoritative lifecycle checks, ended/expired responses, lease/TTL semantics, write invalidation and forced-refresh behavior. Caches or in-flight work MUST NOT cross users, tokens or sessions, hide errors or increase continuous polling. Existing Global time memberships, billing/quotas, Creem, models, prompts, feature switches, languages and unrelated functionality SHALL remain unchanged.

#### Scenario: Authorization or lifecycle changes during a read
- **WHEN** membership, permission, binding or session lifecycle is revoked, ended or replaced while a read is cached or in flight
- **THEN** the existing authoritative denial/invalidation and freshness limits remain and an obsolete response cannot restore access or overwrite current state

#### Scenario: A completed state-changing action requires a refresh
- **WHEN** existing Global behavior requires fresh state after a write or forced refresh
- **THEN** request coalescing or caching cannot satisfy it with obsolete state or cross-account data

### Requirement: Necessary screenshot reads remain device scoped and read only
If admitted by the reviewed allowlist, the existing device next-request endpoint SHALL support optional sessionId/requestId parameters with current binding and owner/session/device/code checks. The no-query contract SHALL remain unchanged. Scoped reads MUST NOT claim, mutate, bill or invoke models; mismatched records MUST NOT be returned.

#### Scenario: A device has old pending requests from another session
- **WHEN** a current device requests its current session or a specific request
- **THEN** the response includes only authorized matching data, including matching terminal states needed to skip cancelled work, without exposing or capturing another session

### Requirement: Global Web download metadata is a minimal compatible delta
Global Web changes SHALL be restricted to the actual active static graph's three official companion download entries, index fallback links and necessary cache-safe resource references/build marker. All original235 files SHALL remain available. The existing1.5-second state cache, request coalescing, UI, supported languages, SEO, commercial behavior, Nginx/CSP and mock/state/cancellation code SHALL remain unchanged. Whole-source rebuild success SHALL NOT be treated as proof of equivalence or permission to import CN Web changes.

#### Scenario: A current download entry still names1.3.5
- **WHEN** all three verified Global1.3.6 artifacts and metadata are ready
- **THEN** only the three exact metadata entries and fallback links change to the verified version, with necessary new cache-safe resource references and all old assets retained

#### Scenario: A shared frontend source contains unrelated CN changes
- **WHEN** assembling Global Web candidates
- **THEN** those changes are excluded and the existing Global state/cache/paid and language behavior remains byte-identical except necessary resource references
