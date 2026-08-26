## ADDED Requirements

### Requirement: Visible live page owns the browser subscription
For one browser and interview session, the system SHALL allow at most one eligible page to own the realtime subscription, and a hidden or frozen page MUST NOT retain ownership when a visible page can take over.

#### Scenario: Current leader becomes hidden
- **WHEN** the current realtime leader page changes from visible to hidden
- **THEN** it releases leadership, cancels its active SSE stream, and stops leader heartbeats without stopping desktop audio capture

#### Scenario: Visible follower receives release
- **WHEN** an eligible visible follower receives the current leader's release message
- **THEN** it immediately becomes the leader, refreshes its server page lease, and starts one realtime subscription

#### Scenario: Two pages remain visible
- **WHEN** two eligible pages for the same interview are visible concurrently
- **THEN** deterministic election and the server page lease keep at most one page subscribed and the follower consumes relayed state

### Requirement: First authoritative snapshot has a bounded deadline
The Web realtime consumer MUST receive and apply the first authoritative SSE snapshot within a two-second client deadline after a successful response, or terminate that stream attempt as a recoverable first-snapshot timeout.

#### Scenario: Response headers arrive without a snapshot
- **WHEN** the SSE request succeeds but no valid snapshot is parsed within two seconds
- **THEN** the reader is cancelled, all deadline resources are cleared, and the caller receives a recoverable timeout classification

#### Scenario: Snapshot arrives before the deadline
- **WHEN** a valid authoritative snapshot is parsed before two seconds
- **THEN** the deadline is cancelled, the stream becomes healthy, and subsequent ordered updates continue on the same connection

### Requirement: Recovery is immediate after an authoritative fallback
The visible leader SHALL load at most one aggregate recovery snapshot after an unhealthy SSE attempt. If that recovery succeeds, it MUST apply the state and rebuild SSE immediately without waiting for the accumulated exponential retry schedule; if recovery fails, retries MUST remain non-overlapping and bounded.

#### Scenario: Initial stream times out and recovery succeeds
- **WHEN** the initial SSE misses its first-snapshot deadline and the aggregate snapshot request succeeds
- **THEN** the page displays the recovered state and starts a new SSE attempt without a 2/4/8/15-second delay

#### Scenario: Stream and recovery both fail
- **WHEN** both the SSE attempt and aggregate recovery fail
- **THEN** the page schedules one retry using bounded backoff and does not create parallel streams, snapshots, or timers

### Requirement: Healthy delivery remains push-only and monotonic
After the first authoritative snapshot, the page MUST consume the existing cursor-ordered SSE without periodic transcript/runtime polling, and recovered or relayed state MUST NOT overwrite newer transcript revisions or final states.

#### Scenario: Healthy stream receives partial revisions
- **WHEN** ordered partial revisions arrive on a healthy SSE
- **THEN** the visible page applies the newest revision without waiting for a periodic refresh or browser paint callback

#### Scenario: Page returns to the foreground
- **WHEN** a previously hidden page becomes visible and regains ownership
- **THEN** it resumes from the stored cursor or aggregate snapshot and preserves monotonic transcript and terminal state

### Requirement: Delivery recovery diagnostics remain content-free
The system MUST record connection, first-snapshot timeout, recovery and reconnect timing without including transcript text, audio, credentials or personal profile content.

#### Scenario: First-snapshot timeout is observed
- **WHEN** a first-snapshot timeout triggers recovery
- **THEN** diagnostics record only session-safe identifiers, timing, reason and connection state
