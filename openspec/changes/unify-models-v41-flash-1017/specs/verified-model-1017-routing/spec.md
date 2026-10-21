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
The delivery SHALL contain region-specific candidate configuration deltas, tests/evals and verification records on branches derived from the confirmed regional tags. It MUST NOT deploy, restart services, alter live environment files, push Git or change unrelated components. Future deployment SHALL require fresh explicit authorization and complete protected-work gates, including active resume optimizer jobs.

#### Scenario: Local implementation finishes
- **WHEN** available compatibility checks pass
- **THEN** the result states exactly which region/components are ready, any limitations and how a later guarded release would replace or roll back them
- **AND** current production images and effective settings remain unchanged

### Requirement: Authorized Global release is minimal and protects real work
The later explicitly authorized Global production phase MUST recheck each component actual runtime baseline, preserve published performance optimizations, independently overlay only its summary non-thinking parameter, and update four Backend selectors plus the existing worker shared selector to1017. Other configuration, APIs, prompts, language, commercial rules, Web and non-target components MUST remain unchanged.

#### Scenario: Existing Global performance parity is present
- **WHEN** fresh actual source manifests match published auth, state and prefetch optimizations
- **THEN** the release records parity and preserves it without recopying unrelated CN files

#### Scenario: Protected work or unknown state exists
- **WHEN** ordinary/mock/preparation/companion/audio/answer/screenshot/material/optimizer/financial work or Backend TCP connections are active or unreadable
- **THEN** deployment and recovery defer without terminating or clearing user work

#### Scenario: Candidate changes a non-target
- **WHEN** complete candidate source, Settings, routes, schema, private context or non-target identity differs outside the exact allowlist
- **THEN** the controller rejects the release without bypassing the check

#### Scenario: Independent components pass verification
- **WHEN** local regressions and pinned actual-image probes pass and fresh complete gates are idle
- **THEN** the controller replaces only Backend and material-worker, preserves pinned guarded recovery, independently verifies actual ownership/configuration, and records short sanitized error counts
- **AND** it reports evidence limits without claiming measured P95 improvement from synthetic tests
