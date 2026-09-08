## ADDED Requirements

### Requirement: Live-answer streaming uses isolated bounded admission
The system SHALL execute synchronous live-answer generation outside the shared framework thread pool through a bounded executor, and MUST keep concurrent work and buffered SSE events bounded.

#### Scenario: Shared request workers are busy
- **WHEN** status, heartbeat, polling or other synchronous requests occupy shared request workers while a user starts quick answer
- **THEN** the accepted quick-answer stream is admitted through the dedicated bounded answer path without waiting for an unrelated shared-worker slot

#### Scenario: Answer capacity is exhausted
- **WHEN** the bounded answer executor and its waiting capacity are full
- **THEN** the system fails the new answer safely without charging twice, leaking a worker or creating an unbounded queue

### Requirement: First answer output is not intentionally delayed
The Global Web SHALL render the first non-empty answer update without applying the normal follow-up chunk coalescing delay, while later updates MAY remain coalesced to protect rendering performance.

#### Scenario: Provider emits the first visible answer chunk
- **WHEN** the browser parses the first non-empty answer chunk for a task
- **THEN** it schedules that update immediately and continues to acknowledge first render at most once

### Requirement: Stream entry timing is observable and content free
The system SHALL record route receipt, dedicated executor admission, answer-generator start, provider request, first provider token, first visible output and SSE yield timestamps without storing question, answer, transcript or material content.

#### Scenario: First visible answer is acknowledged
- **WHEN** the browser acknowledges the first rendered answer
- **THEN** diagnostics can distinguish route-to-executor wait, executor-to-generator wait and existing provider/render stages using opaque identifiers and timestamps

### Requirement: Existing answer semantics remain unchanged
The optimization MUST preserve model and prompt selection, question normalization, selected-material grounding, RAG policy, quick/detail order, billing admission and settlement, cancellation, retry, history, terminal task state and public request compatibility.

#### Scenario: Existing answer regression suite runs
- **WHEN** quick answer is exercised with materials, billing, cancellation, retry, Chinese and English language settings
- **THEN** content, ordering, ownership, charges and terminal states match the existing contract

### Requirement: Pilot deployment is isolated from Chinese production
The first production rollout SHALL rebuild and replace only the independent Global Backend and Global Web after preserving their rollback images, and MUST NOT build, restart or reconfigure any Chinese production service.

#### Scenario: Global pilot is deployed
- **WHEN** local verification passes and Global has no active interview workload
- **THEN** only `offersteady.com` services are replaced, Global and Chinese health checks pass, and the prior Global release remains recoverable
