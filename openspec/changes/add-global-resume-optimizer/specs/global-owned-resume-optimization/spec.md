## ADDED Requirements

### Requirement: Global owned resume inputs
The Global application SHALL expose an English Resume Optimizer journey for an authenticated user to select or upload their own ready resume and optionally provide a target role and their own ready JD or bounded pasted JD text. The service MUST bind inputs to document versions and reject unavailable, deleted, wrong-kind, cross-owner or stale inputs without invoking a model.

#### Scenario: General review without a JD
- **WHEN** an eligible owner selects a ready resume without a JD
- **THEN** the task SHALL be created for general resume review and the UI SHALL state that role matching is not assessed

#### Scenario: Versioned resume and JD
- **WHEN** an eligible owner supplies a ready resume and an owned ready JD version
- **THEN** the service SHALL bind both immutable version identifiers and the result SHALL identify which inputs were used

#### Scenario: Invalid or foreign input
- **WHEN** a user supplies another owner's document, a deleted/processing document, or a mismatched version
- **THEN** the service SHALL reject the task and SHALL NOT read or reveal the document body or start provider work

### Requirement: Lossless controlled table normalization at optimizer input
The optimizer input reader SHALL support HTML tables retained in existing Parser Markdown by converting only controlled table/row/cell/group/break tags to separated plain text with `HTMLParser`, preserving every cell's text, numbers, dates, contacts, entities and order. The same normalized source copy MUST be used for displayed `sourceText`, provider input, evidence quotes and conservative rewrite anchors. Original material bytes, Parser artifacts, document versions and interview snapshots MUST remain unchanged. Unsupported or malformed HTML MUST fail before daily reservation or provider work, with actionable English guidance, without script/style evaluation, remote fetch, silent stripping or content truncation.

#### Scenario: Parsed resume contains a MinerU HTML table
- **WHEN** an owned ready resume artifact contains supported HTML table rows and cells with employers, dates, metrics, contact details and character entities
- **THEN** admission SHALL retain every cell's complete factual content and separated structure in one normalized source copy
- **AND** displayed source, model input and literal evidence/rewrite validation SHALL use exactly that copy while the original uploaded file and Parser artifact remain byte-identical

#### Scenario: Source contains unsupported or executable HTML
- **WHEN** a source contains unsupported/malformed markup, script/style content or external-resource tags
- **THEN** admission SHALL reject it with clear English recovery guidance before reserving a daily use or invoking a model
- **AND** it SHALL NOT execute or fetch anything, silently drop content or publish an incomplete source

### Requirement: Daily benefit for every valid paid time membership
The service SHALL allow every currently valid paid time-membership user, including a one-day plan user, one free optimization per UTC calendar day. A non-member MUST receive an upgrade-membership state; a member whose current-day allowance is exhausted MUST receive a wait-until-next-day state with the next UTC reset time. This Global feature MUST NOT introduce points, a new wallet or an extra paid-use entry, and MUST NOT alter other Global membership, Creem, minutes or mock-interview entitlements.

#### Scenario: Member uses the daily free optimization
- **WHEN** a currently valid paid time-member with an unused allowance confirms an optimization
- **THEN** the server SHALL atomically reserve that UTC day's one free use before queue admission
- **AND** all time-plan durations, including one day, SHALL qualify under the same rule

#### Scenario: Non-member requests optimization
- **WHEN** a user without a valid paid time membership creates an optimization
- **THEN** the server SHALL reject the task with upgrade-membership guidance before provider work and SHALL NOT offer a points or per-use payment path

#### Scenario: Member exceeds daily allowance
- **WHEN** a member with that day's free allowance already reserved or used creates another optimization
- **THEN** the server SHALL reject creation with next-day guidance and the next UTC reset time without using other product quotas

#### Scenario: UTC day boundary
- **WHEN** a member creates the first eligible job after UTC midnight
- **THEN** the new UTC day's free allowance SHALL be independent of the prior day and a delayed release from a prior-day job SHALL NOT add extra free uses to the new day

### Requirement: Atomic idempotent use and release
A job SHALL atomically reserve its creation UTC day's one free use before queue admission and SHALL mark it used only after successful completed delivery. Failed, cancelled or source-deleted undeliverable jobs MUST release that original reservation exactly once. Retrying new generation MUST re-check current membership and allowance. Reading, editing, exporting and save-as of an existing completed result MUST NOT consume another use and SHALL remain available to its owner after membership expiry while its task/sources remain undeleted.

#### Scenario: Duplicate creation or completion
- **WHEN** identical creation or completion operations are replayed for a job
- **THEN** exactly one daily use SHALL be reserved/used and duplicate provider work SHALL NOT be enqueued

#### Scenario: Generation fails or is cancelled
- **WHEN** a reserved job fails validation, times out, is cancelled or becomes undeliverable after source deletion
- **THEN** its original creation-day allowance SHALL be released exactly once even if callbacks are replayed

#### Scenario: Concurrent claims for the last free use
- **WHEN** concurrent requests attempt to consume an account's same-day free use
- **THEN** the service SHALL atomically accept at most one eligible job and SHALL prevent duplicate free use

#### Scenario: Owner edits and downloads after membership expiry
- **WHEN** an owner whose membership has expired reads, edits, downloads DOCX/PDF or saves a completed undeleted draft as a new resume
- **THEN** the operation SHALL not require renewed generation entitlement or consume another daily use

### Requirement: Durable bounded task lifecycle
The service SHALL persist owner-bound tasks with queued, running, completed, failed or cancelled states, stable idempotency and bounded inputs/outputs/timeouts. It MUST limit concurrent/queued work and prevent more than one unfinished optimization per account. Failure, cancellation, interruption and retry MUST be visible without masquerading as completion.

#### Scenario: Duplicate create is replayed
- **WHEN** the same owner replays a creation request with the same idempotency key and matching input
- **THEN** the service SHALL return the same task without a second provider invocation or duplicate daily-allowance reservation

#### Scenario: Capacity is exhausted
- **WHEN** per-account or global unfinished capacity is full
- **THEN** the service SHALL reject additional work as busy without an unbounded queue or occupying the interview execution pool

#### Scenario: Provider fails or process is interrupted
- **WHEN** provider work times out, returns invalid output, or a running lease expires after interruption
- **THEN** the task SHALL become a visible failure with a safe retry action and SHALL NOT publish a partial successful resume or blindly repeat provider work

#### Scenario: User cancels work
- **WHEN** the owner cancels a queued or running task
- **THEN** the task SHALL become cancelled and late provider output SHALL NOT complete it

### Requirement: Owned access and complete derived deletion
All task list/detail/edit/export/save-as/cancel/delete operations MUST enforce authentication and ownership. Task deletion or referenced source resume/JD deletion MUST immediately prevent further reads and writes, cancel active work and physically remove stored derived input/result/draft/export content. A separately saved resume SHALL remain a normal independent user material only after explicit user confirmation.

#### Scenario: Another account accesses an optimization
- **WHEN** a different account requests a task or its export, edits, deletion or save-as
- **THEN** the service SHALL deny it without revealing personal content or changing the task

#### Scenario: Source is deleted during generation
- **WHEN** a source resume or referenced JD is deleted while model generation is running
- **THEN** the task SHALL immediately be inaccessible and cancelled, derived content SHALL be cleared, and late completion SHALL NOT restore it

#### Scenario: Task is deleted after completion
- **WHEN** its owner deletes a completed optimization
- **THEN** subsequent reads/downloads SHALL fail and all stored source snapshots, review, draft and generated exports for that task SHALL be removed
- **AND** a resume explicitly saved as independent material before deletion SHALL remain subject to its own normal deletion controls

### Requirement: Disclosed sensitive processing and minimal logs
The UI SHALL explain before submission that resume/JD content is sent to the configured AI service, results are saved with the task, and the owner can delete them. Logs MUST exclude personal document content, contact details, prompts, object keys and provider payloads.

#### Scenario: User starts the workflow
- **WHEN** the owner reaches task submission
- **THEN** an English processing/persistence/deletion disclosure SHALL be visible before confirmation

#### Scenario: Provider or storage error is logged
- **WHEN** a task encounters an exception
- **THEN** persisted logs SHALL contain only safe status/timing/count/error metadata and SHALL NOT include source content or provider payload
