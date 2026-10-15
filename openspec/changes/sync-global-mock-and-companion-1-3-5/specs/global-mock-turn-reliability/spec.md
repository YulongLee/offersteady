## ADDED Requirements

### Requirement: Next generation proceeds while old capture closes
Global mock answer submission SHALL confirm its original answer once, stop and revoke the old capture epoch, and start the next generation without waiting for the upstream ASR close handshake. Actual cleanup SHALL remain bounded and tracked until released. Late audio, transcripts and cleanup SHALL not alter or close a newer round.

#### Scenario: Old provider closes slowly
- **WHEN** a valid answer is submitted and the previous upstream close remains pending
- **THEN** the generating state and next generation proceed, the original answer is retained once, and stale capture input is rejected

#### Scenario: Cleanup observer is cancelled
- **WHEN** a cancelled observer had queued or begun an actual provider close
- **THEN** actual resources are still released exactly once and activity plus closing admission remains within its existing bound

### Requirement: Global microphone cleanup and generation diagnostics are safe
Disconnect cleanup SHALL tolerate a socket already disconnected, release only its own registration, and preserve any replacement connection. Generation diagnostics SHALL distinguish fixed stages and bounded failure categories without logging private content, provider response bodies, secrets or raw exception text. Existing provider calls, retries, output validation and fault accounting SHALL remain unchanged.

#### Scenario: Disconnect races replacement
- **WHEN** the original microphone socket disconnects after a replacement registration
- **THEN** no secondary cleanup traceback occurs and the replacement remains registered

#### Scenario: Provider fails with private markers
- **WHEN** synthetic provider input, output or error includes private markers
- **THEN** diagnostics contain only approved metadata and no markers, with the original retryable state and provider-attempt count

### Requirement: Preserve independent Global product and performance policy
Global SHALL retain seven-day-or-longer plan eligibility, UTC daily-three quota, no CN wallet access, no CN flat-fee or sixty-minute deadline, original language/model/Creem behavior and already published heartbeat/P95 optimizations. Deployment SHALL be based on actual running images and only include verified performance/reliability changes.

#### Scenario: Practice exceeds CN duration boundary
- **WHEN** a valid Global practice continues more than sixty minutes after starting
- **THEN** no CN time-limit end or points fee is applied and the original Global eligibility/quota policy holds

#### Scenario: Existing pages or heartbeats are used
- **WHEN** a normal Global interview, billing page, mock route or heartbeat is used after the update
- **THEN** existing features and authoritative freshness/idle behavior remain available without reverting published performance changes

### Requirement: Lightweight authoritative Global web heartbeat
Normal Global web heartbeat SHALL read only the existing five-field authoritative session projection rather than full session/material context. It SHALL retain ended-session rejection, idle expiry and lease refresh semantics and SHALL preserve existing desktop heartbeat coalescing and request-level P95 diagnostics.

#### Scenario: Heartbeat renews a live page
- **WHEN** a normal authenticated live page sends a heartbeat
- **THEN** authoritative lightweight session state governs acceptance and the lease renews without loading resume/JD/knowledge or full answer context

#### Scenario: Session has ended or changed since prior pulse
- **WHEN** authoritative session state is no longer eligible
- **THEN** the original rejection/expiry behavior applies without trusting a stale client or in-process cache
