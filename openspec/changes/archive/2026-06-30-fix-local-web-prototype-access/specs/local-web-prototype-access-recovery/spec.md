## ADDED Requirements

### Requirement: Local web prototype must be startable and reachable
The system SHALL provide a reliable local access path for the Web prototype so that team members can start the prototype and open the approved pages in a browser before continuing product review or implementation.

#### Scenario: Start local prototype successfully
- **WHEN** a team member follows the documented local startup path
- **THEN** the Web prototype MUST start on a known local address and allow browser access to the landing page

#### Scenario: Distinguish unreachable service from broken page
- **WHEN** the local prototype cannot be opened
- **THEN** the project MUST be able to distinguish whether the cause is service startup failure, wrong local access method, or an actual page/runtime regression

### Requirement: Local review flow must validate access prerequisites
The system SHALL define a local review flow that validates access prerequisites before treating automated review failures as product regressions.

#### Scenario: Review script requires a running local service
- **WHEN** a local automated prototype review is executed
- **THEN** the workflow MUST require a reachable local Web service before interpreting failures as page-level issues

#### Scenario: Verify key local pages after recovery
- **WHEN** local prototype access has been recovered
- **THEN** the landing page, login page, interview home, library, preparation page, live interview page, billing page, and guide page MUST be locally reachable

### Requirement: Access recovery must preserve approved prototype UX
The system SHALL fix local access blockers without silently redesigning approved prototype structure, navigation, or core interaction flow.

#### Scenario: Recovery changes affect prototype pages
- **WHEN** a local access fix touches Web prototype code
- **THEN** it MUST preserve the approved prototype baseline unless a separately approved change explicitly alters product behavior

#### Scenario: Recovery records diagnosis and verification
- **WHEN** a local access problem is fixed
- **THEN** the project MUST document the diagnosed cause, the fix path, and the verification steps used to confirm local access recovery
