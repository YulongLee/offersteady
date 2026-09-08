## ADDED Requirements

### Requirement: Chinese live answers use isolated bounded admission
The Chinese Backend SHALL execute the synchronous live-answer iterator through the dedicated bounded live-answer executor and bounded event bridge without changing request, response, answer-content or billing semantics.

#### Scenario: Capacity is available
- **WHEN** a valid Chinese live-answer request is admitted with available executor capacity
- **THEN** the system streams the same answer event contract through the isolated executor instead of competing in the shared default executor

#### Scenario: Capacity is saturated
- **WHEN** the configured live-answer worker and admission capacity is exhausted beyond its timeout
- **THEN** the request fails through the existing controlled error contract without creating an unbounded queue

### Requirement: Entry telemetry is content-free
The Backend SHALL expose route, admission and generator-entry timing without recording question text, answer text, audio, screenshots or user materials.

#### Scenario: Timing is recorded
- **WHEN** a live-answer request reaches the iterator
- **THEN** timing telemetry identifies the pre-generation stages while containing no user content

### Requirement: Chinese rollout occurs only while idle
The release process SHALL replace Chinese Backend/Web only when interview sessions with activity inside the configured idle window, active desktop transports and realtime queue or worker counts are all zero, and SHALL retain the prior release for rollback. Stale live-status rows outside the idle window SHALL be reported but SHALL NOT be modified by this release.

#### Scenario: Activity remains present
- **WHEN** any required Chinese production activity signal is non-zero
- **THEN** the deployment does not build or replace a production service and continues monitoring

#### Scenario: Production is idle
- **WHEN** all required activity signals are zero immediately before cutover and local validation has passed
- **THEN** only Chinese Backend/Web are deployed with recorded rollback images and health checks

### Requirement: Global production remains unchanged
The rollout SHALL NOT deploy, recreate or restart a Global service.

#### Scenario: Chinese release completes
- **WHEN** the Chinese Backend/Web release is deployed
- **THEN** Global service identity remains unchanged and its public health endpoint remains healthy
