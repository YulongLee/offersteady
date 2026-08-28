## MODIFIED Requirements

### Requirement: Confirm the material list without a redundant data-purpose checkbox
The system MUST save the user's explicitly confirmed interview material list, including an empty list, before the interview starts and MUST NOT require a redundant general-purpose data-use checkbox. Start eligibility SHALL require a confirmed material list and at least one usable question-input path; an audio-assisted path SHALL additionally require fresh readiness evidence for every required audio source, while a manual-only path SHALL remain available without audio permission.

#### Scenario: User confirms selected materials
- **WHEN** the user selects materials and confirms the interview material list
- **THEN** the system saves the session selection version and enables start when the selected question-input path is usable

#### Scenario: User confirms an empty list
- **WHEN** the user explicitly confirms an empty resume, JD, and knowledge-material list
- **THEN** the system saves the empty allow-list and permits continuation without an additional general data-use checkbox

#### Scenario: Material list is not confirmed
- **WHEN** the user changes selections without saving confirmation
- **THEN** the system prevents interview start and explains that the interview material list must be confirmed

#### Scenario: Audio-assisted path has not passed sound checks
- **WHEN** the user selects an audio-assisted path but one or more required source checks are absent, stale, or invalid
- **THEN** the system keeps audio-assisted start disabled, identifies the affected source, and offers a recheck without treating permission alone as readiness

#### Scenario: Manual-only path is usable
- **WHEN** the material list is confirmed and the user selects manual input without audio capture
- **THEN** the system permits live entry without requiring microphone or computer-output readiness
