## ADDED Requirements

### Requirement: Shared recoverable runtime state
The backend SHALL store active leases, device binding, transport metadata, channel status, and event cursors in a shared runtime store accessible to all gateway and API workers.

#### Scenario: Backend worker restarts
- **WHEN** one API or gateway worker restarts during an active interview
- **THEN** another worker can reconstruct the authoritative runtime snapshot without requiring machine-code rebinding

### Requirement: Stable desktop identity
The production desktop SHALL preserve its device identifier and credential across relaunches and signed upgrades.

#### Scenario: User installs an upgrade
- **WHEN** a signed newer desktop version replaces the previous version
- **THEN** the existing device identity remains valid and the web binding does not change solely because of the upgrade

### Requirement: Presence is not media authorization
The runtime SHALL distinguish desktop lease, web presence, and interview lifecycle. Loss of web presence alone SHALL NOT immediately revoke a valid desktop media lease.

#### Scenario: User refreshes the live page
- **WHEN** web presence temporarily expires while the interview remains active
- **THEN** desktop transport remains resumable and the refreshed page can reattach without recreating the interview

#### Scenario: Interview ends
- **WHEN** the owner explicitly ends the interview
- **THEN** all desktop leases, provider sessions, and web subscriptions for that interview are revoked

### Requirement: Authoritative lifecycle state machine
The runtime SHALL expose one authoritative state from `paired-idle`, `connecting`, `streaming`, `reconnecting`, `degraded`, and `stopped` transitions.

#### Scenario: Channel reconnects successfully
- **WHEN** a degraded channel reconnects before its lease expires
- **THEN** the runtime returns to `streaming` without a duplicate capture owner or provider session

### Requirement: Authoritative privacy pause control
The runtime SHALL persist an explicit session-scoped capture control state, and web, backend ingestion, and desktop capture SHALL all honor that state until the user explicitly resumes or ends the interview.

#### Scenario: User pauses capture from the live workspace
- **WHEN** the owner selects pause during a live interview
- **THEN** the backend records `paused`, rejects new audio from entering ASR, the desktop stops its active publisher, and realtime refresh or reconnect does not restore capture automatically

#### Scenario: User resumes capture explicitly
- **WHEN** the owner selects resume for the same live interview
- **THEN** the backend records `capturing` and the bound desktop may create one authoritative publisher and resume both role channels

### Requirement: Session-scoped realtime hot state
The runtime SHALL validate transport ownership at connection time and SHALL keep accepted per-frame work independent from PostgreSQL and global Redis snapshot serialization.

#### Scenario: Audio frame is accepted
- **WHEN** an authenticated connection sends the next valid channel sequence
- **THEN** the gateway updates session-local sequence and receipt state without opening a PostgreSQL connection or rewriting unrelated sessions

#### Scenario: Publisher lifecycle is unchanged
- **WHEN** another partial audio revision is processed successfully
- **THEN** no redundant publisher lifecycle snapshot is written
