## ADDED Requirements

### Requirement: Duplicate active-connection read protection
The backend SHALL coalesce or briefly cache identical concurrent desktop active-connection reads without changing the authoritative binding result.

#### Scenario: Identical reads arrive concurrently
- **WHEN** requests use the same device, code and pinned binding identifiers while state is unchanged
- **THEN** equivalent work SHALL be reused and equivalent responses returned

#### Scenario: Binding identity changes
- **WHEN** pinned session or binding identifiers change
- **THEN** the previous identity result SHALL be bypassed

#### Scenario: Binding state mutates
- **WHEN** registration, binding, session status or ownership changes
- **THEN** the transition SHALL be visible within the existing freshness budget

### Requirement: Control protection preserves core behavior
Protection SHALL NOT rate-limit realtime operation or modify audio, ASR, transcript, quick-answer or screenshot semantics.

#### Scenario: Normal live interview
- **WHEN** one valid Companion performs live checks
- **THEN** the existing refresh interval and all capabilities SHALL remain available

### Requirement: Privacy-safe observability
Verification SHALL use only aggregate request counts, latency classes, status codes and anonymous counts.

#### Scenario: Production comparison
- **WHEN** operators compare rollout metrics
- **THEN** user content, credentials and full personal identifiers SHALL be excluded
