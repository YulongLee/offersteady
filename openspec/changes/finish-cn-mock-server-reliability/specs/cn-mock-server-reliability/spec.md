## ADDED Requirements

### Requirement: Advance CN submissions independently of old ASR shutdown
An accepted CN mock answer SHALL persist the next phase, stop interaction time and revoke the old capture before publishing generation and starting the next job. It MUST NOT wait for the old provider close handshake. Original owner/version/submission idempotency, server deadline and provider-fault accounting SHALL remain unchanged.

#### Scenario: Old close blocks
- **WHEN** a valid CN submission succeeds but its old ASR close remains blocked
- **THEN** generating state and the next job start while cleanup is pending, with no extra charge, duplicate job, or old transcript admitted

#### Scenario: Submit is duplicated or stale
- **WHEN** the original submission is retried or an old version/epoch arrives
- **THEN** original idempotency and phase protections remain effective and no new generation or capture is allocated by the stale input

### Requirement: Track detached cleanup through actual completion
Detached ASR close SHALL use bounded execution and retain tracking of its actual future until completion. Observer cancellation or drain timeout MUST NOT abandon or cancel the underlying native close. New capture and replacement microphone registrations SHALL remain isolated from old cleanup. Existing CN stop/shutdown and Global waiting policies SHALL remain.

#### Scenario: Observer is cancelled while native work is active or queued
- **WHEN** a cleanup observer is cancelled before starting or during an actual close
- **THEN** real work remains tracked and drain observes its completion without affecting a new round

#### Scenario: A replacement connection exists
- **WHEN** an old capture or microphone endpoint finishes cleanup after its replacement is registered
- **THEN** the replacement remains registered and its capture is not closed

### Requirement: Close disconnected CN microphone endpoints idempotently
CN mock microphone cleanup SHALL tolerate an already disconnected socket raising WebSocketDisconnect while preserving registration ownership and existing pause/meter behavior. This cleanup MUST NOT generate a secondary unhandled disconnect traceback.

#### Scenario: Peer is already disconnected
- **WHEN** final socket close raises WebSocketDisconnect after the endpoint has released its own registration
- **THEN** cleanup returns safely and does not close or unregister a replacement

### Requirement: Diagnose generation and cleanup without sensitive content
CN mock diagnostics SHALL record allowlisted stage, outcome, nonnegative duration and bounded error category, optionally with a valid HTTP status. Generation events SHALL use random task-local trace identifiers without user/session/device identifiers. Unknown fields/values MUST NOT echo inputs; private content, credentials, URLs, provider bodies and raw exception text MUST NOT be emitted. Diagnostics MUST NOT alter model inputs, output validation, provider call count, retries, cancellation, billing or Global behavior.

#### Scenario: Provider or output fails
- **WHEN** a synthetic HTTP, queue/request timeout, transport, malformed/incomplete/repeated question or invalid report evidence failure occurs
- **THEN** fixed safe categories identify its stage, no extra provider call occurs and original retry/fault behavior remains

#### Scenario: A job is cancelled or reaches its fixed deadline
- **WHEN** generation is cancelled or its server deadline expires
- **THEN** cancellation remains cancellation, the claim is released or expiry completed through original rules, and safe timing is recorded without reviving a question

#### Scenario: Concurrent jobs contain sensitive markers
- **WHEN** two synthetic jobs run concurrently with private markers embedded in inputs, endpoints, exceptions and outputs
- **THEN** emitted generation traces remain distinct and contain none of those markers

#### Scenario: Another edition or feature runs
- **WHEN** Global mock, ordinary/written interview, resume optimization or membership billing is used
- **THEN** its existing behavior/configuration remains and this CN diagnostic stream is not enabled for Global
