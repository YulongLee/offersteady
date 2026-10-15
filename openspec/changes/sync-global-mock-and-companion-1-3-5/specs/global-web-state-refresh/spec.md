## ADDED Requirements

### Requirement: Coalesce state reads without mixing identities
Global Web SHALL share concurrent state reads and use a short success-only cache for the same public or authenticated identity. Each caller SHALL receive an independent clone; caller abort SHALL not cancel another caller's shared request. An authentication-header identity change SHALL invalidate private cache and in-flight reuse, and stale earlier identity responses SHALL not populate the new cache.

#### Scenario: Concurrent callers share one ordinary refresh
- **WHEN** concurrent callers request state for the same unchanged identity without force
- **THEN** one backend request is shared, each receives its own result, and an aborted caller does not cancel the other caller

#### Scenario: Another account signs in within the cache window
- **WHEN** authentication changes while an old private result or request exists
- **THEN** the new account starts an independent request and receives none of the previous account's cached or late state

### Requirement: Force reload is authoritative after transitions
Force refresh SHALL bypass both success cache and earlier in-flight reuse. Only the current request SHALL populate cache or release its matching in-flight slot. Mutation, session transition and material change callers SHALL force reload when requiring current server state. Failed requests SHALL not populate cache.

#### Scenario: Mutation finishes while an old read is pending
- **WHEN** a caller forces refresh after mutation while an earlier state request is still pending
- **THEN** a new backend request executes and the earlier response cannot overwrite the new authoritative result or cache

### Requirement: Preserve actual Global assets and existing load reductions
The published Web delta SHALL preserve actual Global homepage, lazy entry, authentication, Creem, mock/Word and existing language/realtime behavior, five-second transcript sampling, original Nginx/CSP and old immutable assets. A previously built future image SHALL not be deployed merely because it has a newer tag.

#### Scenario: Candidate is built and checked
- **WHEN** the performance candidate is prepared for release
- **THEN** actual-base provenance and approved function/URL-only differences are demonstrated, browser execution uses the real CSP with synthetic APIs, and old assets remain reachable
