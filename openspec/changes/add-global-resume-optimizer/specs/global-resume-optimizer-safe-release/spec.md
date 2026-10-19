## ADDED Requirements

### Requirement: Isolated Global feature and bounded resource use
The feature SHALL be independently enabled for Global, use an independent bounded execution path, and preserve existing real-time interview models, prompts, processing, billing and capture behavior. Chinese Web/Backend, Admin and desktop companions MUST remain outside this release.

#### Scenario: Optimizer work is queued while an interview is running
- **WHEN** synthetic optimizer tasks are submitted with a synthetic active interview workload
- **THEN** optimizer concurrency/queue limits SHALL remain enforced and interview requests SHALL retain their existing processing and cancellation behavior without using the optimizer queue

#### Scenario: Feature disabled or Chinese deployment
- **WHEN** the new feature is disabled or the deployment is Chinese
- **THEN** no new optimizer provider work SHALL be accepted and existing regional workflows SHALL remain unchanged

### Requirement: Dedicated prompts and synthetic evaluation
New AI behavior SHALL use dedicated versioned Prompt files in `ai/prompts/` and synthetic/regression cases in `ai/evals/`. Test input MUST NOT contain real user resume/JD, audio or session data, and existing interview Prompt/model files MUST remain unchanged.

#### Scenario: Run optimizer verification
- **WHEN** automated evaluation is executed
- **THEN** it SHALL cover numeric preservation, missing facts, JD gaps, malicious source instructions, malformed output and English presentation using synthetic inputs
- **AND** SHALL record exact verification commands/results and genuine unavailable checks

### Requirement: Non-destructive migration and functional self-test
The implementation SHALL provide additive idempotent storage migration and self-tests for owner/version guards, eligibility, task lifecycle/idempotency, timeout/retry/cancel, deletion races, draft conflict, new material persistence, DOCX/PDF validity and English loading/error/empty/progress states. Existing Global account/commerce/material/interview behaviors SHALL be regression checked.

#### Scenario: Repeat migration or roll back application
- **WHEN** the schema upgrade is re-applied or the prior application image is restored
- **THEN** existing tables/content SHALL remain intact and existing application behavior SHALL remain compatible without a destructive down migration

#### Scenario: Self-test before packaging
- **WHEN** the release candidate is prepared
- **THEN** required functional/regression tests, Global typecheck/build, document content/render checks and strict OpenSpec validation SHALL have actual recorded passing results

### Requirement: Actual runtime baseline and protected international release
The release SHALL bind actual running Global target image IDs, source/Prompt inventory, complete runtime routes/schema, effective configuration and non-target identities before modification. It MUST preserve unrelated functions and current auth/state/prefetch optimizations, build fixed candidates with minimal approved changes, and retain fixed rollback configuration.

#### Scenario: Baseline or non-target drift is detected
- **WHEN** deployed source, image, configuration or protected component differs from the frozen expected baseline
- **THEN** automatic cutover SHALL stop and SHALL NOT overwrite the drift with stale source

#### Scenario: Existing Global capabilities are verified
- **WHEN** the new candidate is checked
- **THEN** the original complete runtime route set SHALL remain present, only declared new routes/schema SHALL be added, and Global language, account/Creem/membership/mock flags and current performance fixes SHALL be retained

### Requirement: Wait for real user work before cutover
Before and immediately around deployment/recovery the controller SHALL perform read-only activity gates for regular/mock/written interviews, web/desktop leases, audio tracks, answer/screenshot tasks, material processing and unknown/error states. Any active or unknown work MUST preserve current production and defer cutover without ending interviews, clearing activity, manufacturing idle or relaxing guards.

#### Scenario: Real user remains active
- **WHEN** any protected work or gate read error remains
- **THEN** the service SHALL remain on its current images and publication SHALL wait rather than interrupting users

#### Scenario: Idle verified deployment
- **WHEN** repeated activity gates are idle and baseline/candidate checks pass
- **THEN** only approved Global Backend/Web components SHALL change to fixed candidates, followed by independent health/routes/config/non-target verification and sanitized short error/5xx observation

#### Scenario: Candidate fails verification
- **WHEN** deployed candidate verification fails
- **THEN** recovery SHALL re-check ownership and protected activity before restoring fixed prior images/configuration and SHALL preserve new and existing user data

### Requirement: Explicit regional staging and honest verification limits
The deployment record SHALL distinguish local synthetic checks, actual image checks, short production observation and user acceptance. It MUST not claim real-provider, physical-device, long-term P95 or Chinese deployment acceptance from local tests.

#### Scenario: Global release is reported
- **WHEN** the release is delivered to the user
- **THEN** the record SHALL identify what was deployed and tested, access restrictions and remaining acceptance limits, and SHALL state that China awaits separate authorization after Global validation
