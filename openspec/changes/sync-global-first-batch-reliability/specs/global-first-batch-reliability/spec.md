## ADDED Requirements

### Requirement: Controlled answer startup errors
Global answer startup SHALL preserve existing entitlement rules and return controlled HTTP errors before SSE headers, without unsupported reservation fields or duplicate billing.

#### Scenario: Insufficient entitlement
- **WHEN** an answer reservation is rejected
- **THEN** the API returns the existing business error envelope without TypeError, provider invocation, or an initial HTTP 200 stream

#### Scenario: Successful stream
- **WHEN** startup succeeds
- **THEN** the first event is sent exactly once followed by subsequent events without waiting for the complete model answer

### Requirement: Safe screenshot recovery
Screenshot failure logging SHALL preserve privacy-safe original and recovery error classes and SHALL NOT throw a secondary logging argument error.

#### Scenario: Both completion and recovery fail
- **WHEN** screenshot completion and failure-state recovery raise exceptions
- **THEN** both error classes are logged without raw content and without masking them with a logging TypeError

#### Scenario: Cancelled capture
- **WHEN** a cancelled capture cannot be claimed
- **THEN** recovery does not revive the request

### Requirement: Independent quick-answer completion
The backend and Global Web SHALL finalize simple text independently of detailed output and preserve it through detail failure or cancellation.

#### Scenario: Detailed stage is waiting
- **WHEN** the simple provider finishes and detail is pending
- **THEN** quick-completed is emitted and the simple panel is complete while detail retains its loading state

#### Scenario: Detail fails or delivery is interrupted
- **WHEN** a quick answer has completed before detail fails or delivery ends
- **THEN** already delivered simple text remains visible and is not replaced by an empty answer

#### Scenario: Old task record
- **WHEN** a persisted task lacks the new completion field
- **THEN** decoding succeeds with its compatible default

### Requirement: Global Intel companion release parity
The Global macOS Intel companion SHALL publish version 1.3.2 with verified Developer ID signatures, Apple notarization and Global endpoints, preserving other platform entries.

#### Scenario: Valid artifact
- **WHEN** the x64 artifact passes signature, notarization, architecture and metadata verification
- **THEN** its production object and manifest entry are published without changing arm64 or Windows releases

#### Scenario: Unverified artifact
- **WHEN** signing or notarization fails
- **THEN** no unverified artifact is advertised as a production release

### Requirement: Isolated Global deployment
Deployment SHALL preserve Global multilingual, email authentication, Creem billing and entitlement behavior, leave CN unchanged, and retain a compatible rollback.

#### Scenario: Active interview
- **WHEN** activity checks find ongoing interviews, live-page leases, recent audio or unfinished answers
- **THEN** the service switch waits without stopping users

#### Scenario: Idle release
- **WHEN** candidate tests and immediate activity gates pass
- **THEN** only scoped Global services are switched, verified healthy and checked against tested source hashes

#### Scenario: Rollback with new task data
- **WHEN** rollback reads a task carrying quick_answer_completed
- **THEN** its decoder succeeds without removing user data
