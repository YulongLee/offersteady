## ADDED Requirements

### Requirement: Reject unverified Global source releases
The deployment tooling MUST reject missing or invalid Global release evidence before modifying files or containers. A valid manifest SHALL identify the Global edition, release, intended deployment mode, expected services and baseline image IDs, complete source inventory and reviewed test evidence hashes. Paths MUST be relative, contained, non-symlink paths and MUST NOT include environment or private-key files.

#### Scenario: Source changes after verification
- **WHEN** a covered source file is added, removed or modified after the manifest was reviewed
- **THEN** validation fails and the legacy deployment entrypoint does not build or restart containers

#### Scenario: Incremental manifest supplied to legacy deploy
- **WHEN** an incremental four-component release manifest is supplied to the legacy full Compose entrypoint
- **THEN** the entrypoint rejects it rather than rebuilding a different set of services

#### Scenario: Evidence is missing or changed
- **WHEN** required test evidence is absent, not marked passed or its file hash differs
- **THEN** validation fails without printing private configuration

### Requirement: Plan image retention conservatively
The retention tool SHALL only read Docker metadata and produce a plan, never delete images or data. It MUST protect images used by any running or stopped container, explicit rollback images, and the two most recently created distinct images for each known Global component. Unrecognized or ambiguous images MUST be retained with a reason.

#### Scenario: Old image is still referenced
- **WHEN** an image is older than the two newest versions but used by a stopped container or named rollback reference
- **THEN** the plan retains it and records that reason

#### Scenario: Multiple tags and foreign repositories
- **WHEN** a Global image is also tagged under an unrelated repository
- **THEN** the plan retains it instead of recommending deletion of a shared image ID

#### Scenario: Incomplete inventory
- **WHEN** Docker inventory is missing a container image or an explicit rollback reference cannot be resolved
- **THEN** the planner fails instead of producing deletion candidates from incomplete metadata

### Requirement: Verify the current product contract
Global frontend tests SHALL record the current deployed static landing page, dynamic page and commerce catalogue contract. Any conflict with historical requirements MUST be explicitly recorded without silently changing product behavior or historical specifications. Validation reports MUST distinguish executed tests, skipped prerequisites and pending real-device acceptance.

#### Scenario: Deprecated assertion conflicts with current release
- **WHEN** the old test expects a superseded marketing placement or catalogue label
- **THEN** the replacement test verifies current behavior and keeps meaningful regression coverage rather than skipping the case
