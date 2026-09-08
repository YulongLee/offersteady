## ADDED Requirements

### Requirement: Duplicate active-connection read protection
The backend SHALL coalesce or briefly cache identical concurrent desktop active-connection reads without changing the authoritative binding result.

#### Scenario: Identical reads arrive concurrently
- **WHEN** multiple requests use the same device, manual code and pinned binding identifiers while binding state is unchanged
- **THEN** the backend SHALL avoid repeating equivalent expensive resolution work and SHALL return equivalent response envelopes

#### Scenario: Binding identity changes
- **WHEN** a request has a new pinned session or binding identifier
- **THEN** it SHALL bypass any result associated with the previous identifiers and resolve the authoritative current binding

#### Scenario: Binding state mutates
- **WHEN** registration, binding, session status or ownership changes
- **THEN** a subsequent active-connection read SHALL observe that transition within the existing live polling freshness budget

### Requirement: Control protection preserves core behavior
Duplicate-read protection SHALL NOT rate-limit valid realtime operation or modify audio, ASR, transcript, quick-answer and screenshot result semantics.

#### Scenario: Normal live interview
- **WHEN** one valid Companion performs binding checks during a live interview
- **THEN** the existing live refresh interval and all capture and answer capabilities SHALL remain available

### Requirement: Privacy-safe observability
Verification SHALL measure request counts, latency classes, status codes and aggregate device/session counts without recording user content.

#### Scenario: Production comparison
- **WHEN** operators compare control-plane traffic before and after deployment
- **THEN** the report SHALL exclude audio bytes, transcripts, screenshots, document content, credentials and full personal identifiers
