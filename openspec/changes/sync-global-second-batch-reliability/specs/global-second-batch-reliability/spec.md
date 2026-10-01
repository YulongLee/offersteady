## ADDED Requirements

### Requirement: Bounded visible material processing
Global material processing SHALL preserve durable retry scheduling and track results for a bounded approximately 90-second window without polling after unmount or a terminal state.

#### Scenario: Retry is scheduled
- **WHEN** document processing returns QUEUED after scheduling a recoverable retry
- **THEN** the worker does not overwrite the durable retry with a terminal failure

#### Scenario: Slow success and exhausted retry
- **WHEN** processing succeeds after the former 17-second window or exhausts retries
- **THEN** the page converges to ready or failed, and failed documents are not advertised as usable

#### Scenario: Wait timeout or navigation
- **WHEN** the wait budget expires or the component unmounts
- **THEN** polling stops; timeout reports continued background processing, while navigation aborts silently

### Requirement: Answer cancellation converges
Unfinished Global answer streams SHALL cancel their owned task on producer closure, preserve already generated text, release the existing reservation and retain cancellation against late writes.

#### Scenario: Client disconnects before completion
- **WHEN** the producer is closed after a task starts but before a terminal event
- **THEN** the underlying iterator is closed and the task is cancelled with the existing idempotent billing release and auto-answer claim cleanup

#### Scenario: Normal completion
- **WHEN** a completed or failed terminal event has been produced
- **THEN** stream cleanup does not introduce an extra cancellation or entitlement change

#### Scenario: Late completion after cancellation
- **WHEN** a worker attempts to save completed, failed or streaming state for an already cancelled task
- **THEN** the repository retains the cancelled task and its preserved answer text

### Requirement: Safe Global member administration
Global operators SHALL search and page through member results, see registration times in UTC, and operate only on the currently verified identity using existing Global membership APIs and permissions.

#### Scenario: Search and pagination
- **WHEN** the operator searches and advances a page
- **THEN** the query is preserved, the offset changes in bounded pages, and previous selection is cleared

#### Scenario: Stale search or detail response
- **WHEN** an older request returns after a newer query or member selection
- **THEN** it cannot replace the newer results or selected identity

#### Scenario: Registration timestamp
- **WHEN** a member has a valid millisecond registration timestamp
- **THEN** list and detail show the same explicit UTC time; missing or invalid timestamps show a placeholder

#### Scenario: Repeated or uncertain write
- **WHEN** a grant or revoke is double-clicked or retried unchanged after failure
- **THEN** only one concurrent command is sent, unchanged retries reuse the same idempotency key, and confirmation identifies the exact member and action

#### Scenario: Successful write but failed refresh
- **WHEN** the membership command succeeds but the subsequent detail fetch fails
- **THEN** the interface reports success with a refresh warning and does not automatically issue another membership command

### Requirement: Isolated tested release
Deployment SHALL target only Global Backend, Web, Admin and Material Worker after tests and activity gates, preserving existing configuration, Global features, data and rollback images.

#### Scenario: Busy system
- **WHEN** interviews, recent preparation/audio/pages, unfinished answers or running material jobs exist
- **THEN** deployment waits and does not stop those tasks

#### Scenario: Verified release
- **WHEN** the idle candidate is deployed
- **THEN** source/assets match tested hashes, Global auth/languages/Creem remain available, and CN, databases, Redis, analytics and desktop releases remain unchanged
