## ADDED Requirements

### Requirement: Provider connectivity is verified before candidate implementation
The operator MUST verify the exact `deepseek-v4.1-flash-1017` model through each region's existing text and vision bindings using bounded synthetic inputs. Credentials and private endpoint values MUST remain server-side; probes SHALL NOT create product sessions, jobs or usage records or mutate running configuration.

#### Scenario: Synthetic text and image calls succeed
- **WHEN** the existing bindings return complete correct synthetic text and image answers from1017
- **THEN** that region is eligible for local candidate implementation and extended adapter verification
- **AND** results record model, region, fixed operation, status, checks and timings without secrets or user data

#### Scenario: Binding or model fails
- **WHEN** a request fails, lacks credentials, returns incomplete content or the live image has drifted
- **THEN** the probe fails closed and production remains unchanged
- **AND** the failed capability is not reported as ready for replacement

### Requirement: Candidate routing retains independent model selectors
Approved local candidates SHALL set the existing shared text, quick, detailed and screenshot vision selectors to1017 without merging their routing. Each material worker SHALL use its own supported text settings and runtime baseline. Non-model feature flags, billing, prompts, original resume generation/PDF behavior and other model settings MUST be preserved.

#### Scenario: All backend answer paths are exercised
- **WHEN** synthetic quick, detailed, continuation, resume, mock or screenshot requests are generated
- **THEN** the applicable request uses the exact candidate model and existing protocol/output contract
- **AND** Global disabled mock and web features remain disabled

#### Scenario: Older worker is prepared
- **WHEN** a worker lacks backend-only selectors or modules
- **THEN** preparation changes only its supported shared text model and necessary independently tested non-thinking parameter
- **AND** it does not acquire new backend APIs or business behavior

### Requirement: Existing adapters pass bounded synthetic compatibility checks
Verification MUST exercise current content parsing and safety guards without weakening them. It SHALL include text streaming/non-thinking, single/four ordered screenshots, each enabled resume provider, CN mock question/report, both worker summaries and CN Responses web search. Failures or untested cases MUST be explicit; small-sample durations MUST NOT be described as production P95 or universal quality improvement.

#### Scenario: Four screenshots are submitted
- **WHEN** the existing gateway receives four synthetic JPEG inputs in capture order
- **THEN** one1017 request reads all four and produces one complete checked answer
- **AND** prior single-image, cancellation and usage semantics remain covered by local regression tests

#### Scenario: Structured resume or mock output is returned
- **WHEN**1017 returns content to the current provider
- **THEN** its current schema, language, factual evidence and completion validators accept valid content and reject invalid content
- **AND** no JSON repair or fallback is silently counted as successful remote generation

#### Scenario: Search is verified
- **WHEN** CN's existing Responses gateway calls1017 with its search tool
- **THEN** the synthetic verification distinguishes actual successful grounded search from unavailable/local fallback

### Requirement: This delivery remains local and reviewable
The initial local-verification delivery SHALL contain region-specific candidate configuration deltas, tests/evals and verification records on branches derived from the confirmed regional tags. That initial delivery and its probes MUST NOT deploy, restart services, alter live environment files, push Git or change unrelated components. A subsequent production release phase SHALL require fresh explicit authorization and complete protected-work gates, including active resume optimizer jobs. Historical verification records MUST retain the actual state at the time they were produced.

#### Scenario: Local implementation finishes
- **WHEN** available compatibility checks pass
- **THEN** the result states exactly which region/components are ready, any limitations and how a later guarded release would replace or roll back them
- **AND** current production images and effective settings remain unchanged

### Requirement: An explicitly authorized CN release preserves exact component scope
After the user's subsequent 2026-10-21 CN deployment instruction, a CN production release MAY change the existing four Backend and three material-worker model environment selectors to1017 after tests pass. Each component MUST retain its own verified runtime image and all non-model configuration, endpoint values, source inputs, prompts, billing and API routes. Global, companion applications and Git publication MUST remain outside this release. A coordinated upload gateway fix SHALL follow its separately specified narrow configuration delta.

#### Scenario: CN model selectors are released
- **WHEN** fresh actual CN component baselines match and all local compatibility checks and protected-work gates pass
- **THEN** Backend changes only its shared, quick, detail and vision model environment values and material-worker changes only its three existing text model values
- **AND** effective Settings, health, source and route invariants are verified after cutover without exposing private configuration

#### Scenario: Work exists or the release baseline has drifted
- **WHEN** any interview, preparation/page lease, audio/connection, unfinished answer, material job, resume optimizer job or unfinished billing work is present, a required state is unknown, or a baseline/configuration ownership check fails
- **THEN** the release MUST preserve the current service and refuse automatic cutover
- **AND** it MUST NOT end user work, reap jobs, alter user data or relax guards to force progress

#### Scenario: Candidate fails acceptance
- **WHEN** acceptance fails after a candidate cutover
- **THEN** rollback MUST verify configuration ownership and the same protected-work gates before restoring the pinned original component configuration

### Requirement: CN release gates distinguish abandoned reservation inventory from running answers
The CN release gate SHALL preserve all active-work, unknown-state, index-reservation, checkout and callback protections. Only a `reserved` record whose usage kind is exactly `answer`, whose positive creation time is strictly earlier than both the effective application reservation TTL cutoff and the pinned original Backend process start MAY be reported as historical orphan inventory instead of executing financial work. This classification SHALL rely on the verified process-local answer implementation and its release-before-replay behavior; it SHALL NOT change the reservation or any balance. Its original process anchor MUST be derived from the fresh baseline, bound to the release input and manifest, and rechecked against the frozen original container snapshot on every gate execution.

#### Scenario: Expired answer reservation outlives its original Backend process
- **WHEN** a reserved answer predates the pinned original Backend process and is older than the effective application TTL
- **THEN** the gate MAY report it as informational historical orphan inventory without modifying business data
- **AND** every ordinary/mock interview, page lease, audio/publisher, unfinished answer/capture, material, optimizer and TCP gate SHALL still have to pass independently

#### Scenario: Reservation could belong to current work or has uncertain metadata
- **WHEN** a reservation is within its TTL, was created at or after the original process start, has a nonpositive/null/future creation time, has an unknown state, or belongs to any usage kind other than `answer`
- **THEN** the historical orphan classification SHALL NOT exempt it from protection
- **AND** index reservations SHALL remain protected without this exemption

#### Scenario: A later container restart would widen the orphan cutoff
- **WHEN** the live Backend has been recreated during cutover or recovery
- **THEN** the gate SHALL continue using the frozen original process start and SHALL reject a missing or changed anchor rather than deriving a newer cutoff
- **AND** it MUST preserve non-target components, user data and durable jobs and report the actual result
