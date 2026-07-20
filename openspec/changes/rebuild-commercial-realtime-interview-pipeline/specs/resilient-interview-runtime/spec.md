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
