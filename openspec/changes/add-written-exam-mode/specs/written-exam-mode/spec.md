## ADDED Requirements

### Requirement: Interview and written exam modes have separate workbench entries
The system SHALL expose 面试模式 and 笔试模式 as separate top-level workbench navigation entries. Each entry SHALL show and create only its own session mode. Existing sessions and clients that omit the field MUST remain `interview` sessions.

#### Scenario: User creates a written exam from its dedicated entry
- **WHEN** the user opens 笔试模式, chooses to create a written exam and submits a valid title and role
- **THEN** the backend creates one preparing session with mode `written` and returns that mode to every session client

#### Scenario: User creates an interview from the existing flow
- **WHEN** the user opens 面试模式 and creates an interview
- **THEN** the original interview creation form contains no mode selector and preserves the prior preparation, audio and answer journey

#### Scenario: User views a mode home
- **WHEN** the user opens either top-level mode entry
- **THEN** its current and recent session list excludes sessions belonging to the other mode

#### Scenario: Existing client creates a session
- **WHEN** a client omits the session mode
- **THEN** the backend creates an `interview` session with unchanged preparation, audio, answer and billing behavior

### Requirement: Written exam preparation requires only a connected companion
The written exam preparation page SHALL require an active desktop companion binding and resolved active-session conflict. It MUST NOT require Resume, JD, Knowledge, microphone, system audio or ASR readiness.

The page SHALL use one focused, single-column setup surface. It SHALL show only the companion connection controls, connection/start errors, the mandatory 30-point entry disclosure and the entry action. It MUST NOT render a second explanatory column, a completion counter, repeated capability explanations, a data-processing explanation card or the user's full balance and per-screenshot rate.

#### Scenario: Companion is connected
- **WHEN** a written session has a valid desktop binding and no unresolved active-session conflict
- **THEN** the page enables “进入笔试” without asking the user to select or confirm personal materials

#### Scenario: Companion is not connected
- **WHEN** a written session has no valid desktop binding
- **THEN** the page keeps “进入笔试” disabled and provides the existing secure machine-code or recent-device connection flow

#### Scenario: User views written exam preparation
- **WHEN** a user opens a preparing written session
- **THEN** the page presents one compact companion setup card without duplicated mode, privacy, audio or pricing content

### Requirement: Written exams are isolated from personal materials
The system MUST persist an explicitly empty material scope for a written session and MUST NOT load Resume, JD or Knowledge context for its screenshot answers.

#### Scenario: Account has reusable materials
- **WHEN** a user with existing Resume, JD and Knowledge documents starts a written exam
- **THEN** the written session remains bound to an empty confirmed material set and screenshot provenance reports no personal material use

### Requirement: Written exam runtime is screenshot-only
The written exam workspace SHALL expose screenshot answer and session ending only. The backend and companion MUST NOT start or accept microphone capture, system-audio capture, ASR, transcript, quick answer, manual answer or auto-answer behavior for a written session.

#### Scenario: Written exam starts
- **WHEN** a paid written session enters the active state
- **THEN** the desktop keeps its authenticated device and screenshot event channels but starts no audio publisher, media capture or realtime ASR session

#### Scenario: Unsupported answer action is attempted
- **WHEN** a client calls a realtime speech, quick-answer, manual-answer or auto-answer command for a written session
- **THEN** the backend rejects it with a stable mode-mismatch error without starting work or charging points

#### Scenario: Screenshot answer is requested
- **WHEN** the user clicks 截屏回答 in an active written session
- **THEN** the existing remote capture, upload, vision, streaming answer, history and screenshot-answer billing chain executes normally

### Requirement: Written exam entry costs 30 points once
The system SHALL reserve and settle exactly 30 wallet points once when a written session successfully enters the active state. The entry charge MUST use a session-stable usage identifier, MUST NOT be waived by a time pass, and MUST remain separate from normal screenshot-answer charges.

#### Scenario: Written exam starts successfully
- **WHEN** a preparing written session with at least 30 available points and a valid companion binding starts successfully
- **THEN** the system settles one 30-point `written_exam_entry` usage and exposes the updated balance and auditable ledger entry

#### Scenario: Production billing constraints accept written exam entry
- **WHEN** PostgreSQL reserves and settles a `written_exam_entry` usage
- **THEN** the usage reservation and points-ledger constraints accept the usage kind and its negative settlement entry

#### Scenario: Balance is insufficient
- **WHEN** the user has fewer than 30 available points after existing reservations
- **THEN** the system does not activate the written session and returns an insufficient-balance error without creating screenshot or audio work

#### Scenario: Start request is retried
- **WHEN** the same written session start command is repeated because of retry, refresh or timeout
- **THEN** the system returns the authoritative session and existing charge result without reserving or settling another 30 points

#### Scenario: Activation fails after reservation
- **WHEN** written-session activation fails after the 30 points were reserved
- **THEN** the system releases the reservation and leaves the session preparing

### Requirement: Written sessions can be continued and ended safely
The product SHALL preserve mode-aware navigation, screenshot history and lifecycle state for written sessions while keeping the existing single-active-session rule.

#### Scenario: Preparing written session is reopened
- **WHEN** the user continues a preparing written session
- **THEN** the product returns to the lightweight companion preparation page

#### Scenario: Active written session is reopened
- **WHEN** the user continues an active written session
- **THEN** the product opens the screenshot-only workspace without starting audio

#### Scenario: Written exam is ended
- **WHEN** the user clicks 结束笔试
- **THEN** the session becomes ended, pending screenshot work follows the existing terminal policy, and no further answer or capture command is accepted

#### Scenario: Ended written exam remains discoverable
- **WHEN** a written exam has ended
- **THEN** it remains in 最近笔试 and opens a written-exam result page instead of disappearing from the written journey

#### Scenario: User reviews an ended written exam
- **WHEN** the user opens an ended written session
- **THEN** the result page shows its persisted screenshot questions and answers, returns to 笔试模式, and does not show interview transcript, interview summary or interview-material sections

#### Scenario: End request fails
- **WHEN** the backend rejects or fails an end command
- **THEN** the Web keeps the written workspace visible and does not falsely mark or navigate the session as ended

### Requirement: Mode rollout remains backward compatible and reversible
The database and API SHALL default missing mode values to `interview`, and the release MUST preserve a documented source and image baseline that restores the prior production behavior without data loss.

#### Scenario: Migration is applied to production data
- **WHEN** the mode column is introduced
- **THEN** every existing session is readable as `interview` without changing its lifecycle, material binding, billing or history

#### Scenario: Release is rolled back
- **WHEN** operators restore the recorded pre-feature source and container images
- **THEN** existing interview sessions continue to work and the additive written-mode data does not corrupt prior records
