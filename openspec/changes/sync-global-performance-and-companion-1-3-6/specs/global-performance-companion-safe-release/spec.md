## ADDED Requirements

### Requirement: Candidate releases preserve actual Global runtime boundaries
Every target candidate SHALL derive from its actual running Global image/static byte baseline, contain only the reviewed delta and retain complete expected inputs, effective configuration, dependencies, API contracts, historical assets and non-target component identities. Existing Global commercial, model, feature-switch and language settings SHALL remain. Global Admin, worker, database schemas/volumes and all CN components MUST NOT be replaced.

#### Scenario: A baseline component or configuration has drifted
- **WHEN** preflight, cutover or recovery observes unknown source/image/configuration/Compose/controller differences
- **THEN** automatic switching stops without overwriting the unknown state or using an old directory as a substitute

#### Scenario: A frontend full build contains valid local changes
- **WHEN** preparing a Global production candidate
- **THEN** full-build success alone does not authorize replacing the actual static graph or removing old public assets

#### Scenario: The previously frozen September7 stopped build container exists
- **WHEN** the host includes `zealous_bhaskara`, whose exact ID/image, StartedAt, stopped state, restart count and complete configuration/mount/network signature independently match the October22 frozen non-target
- **THEN** the complete allowed host set is exactly the seven Global services plus this fixed eighth container, it remains the sixth protected non-target without any start/remove/replace/cleanup action, and any signature change, missing expected name or additional unknown container blocks preparation and switching

#### Scenario: The historical stopped container is started or replaced
- **WHEN** its actual signature differs from the fixed verified stopped signature, including lifecycle or identity fields
- **THEN** prepare stops before freezing targets, subsequent verification/recovery also stops, and no gate is weakened or user activity changed

### Requirement: All official objects are verified before version publication
The three Global1.3.6 installers SHALL use independent immutable Global filenames/keys, prohibit overwriting different existing bytes and completely read back length, SHA-256 and MIME before the public manifest advances. The public source of downloads/version gates SHALL be verified from actual runtime, and unrelated latest pointers SHALL not be modified.

#### Scenario: One object is missing or differs
- **WHEN** any target fails upload or complete integrity verification
- **THEN** the existing public manifest remains and none of the three official versions advances

#### Scenario: All objects match
- **WHEN** all three verified Global artifacts are available
- **THEN** the release may atomically publish only their exact filenames, versions, sizes, hashes and Global object keys with retained rollback metadata

### Requirement: Historical static pages retain exact version downloads
The current manifest SHALL retain priority for exact filename lookup. Only Global SHALL fall back to an independent public history file containing the three exact verified previous1.3.5 entries when the current lookup misses. History SHALL NOT enter current public state or the version gate, rewrite old URLs to another version, change old objects or affect CN. Missing/corrupt history and unknown filenames SHALL keep the original unavailable behavior. Both new and rollback Backend candidates SHALL retain this compatibility and the current verified1.3.6 manifest.

#### Scenario: An old cached Global page requests1.3.5
- **WHEN** it requests its original known filename after the official manifest advances
- **THEN** Global resolves the exact old object's preserved metadata and returns the actual1.3.5 bytes while current public versions remain only1.3.6

#### Scenario: History is invalid or the edition is CN
- **WHEN** fallback cannot prove an exact valid Global historical entry or the request is handled by CN
- **THEN** no historical entry is exposed and the original current-lookup/unavailable contract remains

### Requirement: Every disruptive switch waits for all protected user work
Before every component switch or disruptive recovery, the controller SHALL repeat read-only gates for active interviews/preparation, mock practice, audio/publishers, unfinished answers, document/resume/background tasks, valid financial work and relevant TCP/process state. Unknown or failed reads SHALL block cutover. Existing financial anchors SHALL not be reset by new containers. The release MUST NOT end users, clear activity or weaken gates to make deployment pass.

#### Scenario: Another user's interview is active
- **WHEN** any protected user work is still active
- **THEN** the previous service remains running and deployment waits for the user to finish naturally

#### Scenario: A candidate needs rollback while new user work appears
- **WHEN** recovery would interrupt protected work or current ownership is unknown
- **THEN** automatic replacement stops and reports the required disposition rather than forcing an unowned or busy rollback

### Requirement: Publication and uncertain responses are recoverable without duplicate restarts
The release SHALL preserve exact previous manifests, actual images, frozen effective configuration and explicit fixed-image recreation materials. Manifest replacement SHALL be guarded and atomic. A lost response SHALL trigger actual known-state/ownership inspection; a completed release SHALL be verified without repeated restart, and only clearly owned failures with passing gates may use exact recovery. Unknown states SHALL stop.

#### Scenario: SSH loses a cutover acknowledgement
- **WHEN** a switch result is uncertain
- **THEN** the controller proves the actual container/image/manifest state before confirming completion, resuming or restoring and never blindly repeats a restart

#### Scenario: A future recreate uses the release
- **WHEN** rebuilding from preserved materials
- **THEN** it explicitly carries the current active release manifest and fixed candidate configuration, rather than restoring a stale baked-in manifest

### Requirement: Final evidence proves scope and public behavior without user content
Completion SHALL include all three public versions and Range/full download bytes/MIME, original public routes/authentication protections, expected assets/contracts/settings, unchanged non-target services and a bounded sanitized error summary. Evidence SHALL exclude secrets, signed URLs, raw logs and user content/identifiers, and SHALL distinguish synthetic/package checks from real device and long-term P95 acceptance. No real production interview, model call, financial transaction, load test or Git push SHALL be performed as verification.

#### Scenario: The release is reported complete
- **WHEN** deployment and postflight finish
- **THEN** exact package/runtime results, retained Global commercial boundaries, scoped source changes, known physical-device limits and recoverable ownership materials accompany the release record
