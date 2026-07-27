## ADDED Requirements

### Requirement: Unique active live page per user
The system SHALL maintain at most one active live interview page lease for each user, identified by session, page instance, generation, and expiry.

#### Scenario: New page takes over
- **WHEN** a second live page for the same user sends a heartbeat with a different page instance
- **THEN** the system increments the lease generation and makes the second page the only active live page

#### Scenario: Current page renews its lease
- **WHEN** the active page sends another heartbeat before expiry
- **THEN** the system renews the expiry without changing the lease generation

### Requirement: Replaced pages become read-only
The Web application MUST stop realtime requests and answer operations when its live page lease is replaced while preserving already displayed content.

#### Scenario: Same-browser page replacement
- **WHEN** an active page receives a claim broadcast from another page instance
- **THEN** it aborts realtime and answer requests and displays a read-only replacement notice

#### Scenario: Cross-browser page replacement
- **WHEN** an old page heartbeat or stream is rejected by the authoritative backend lease
- **THEN** it enters the same read-only state and does not retry

### Requirement: Preparation does not take over live ownership
The system SHALL allow preparation page heartbeat reporting without replacing the active live page lease.

#### Scenario: Preparation page remains open
- **WHEN** a preparation page sends a heartbeat while another page is live
- **THEN** the active live page lease remains unchanged
