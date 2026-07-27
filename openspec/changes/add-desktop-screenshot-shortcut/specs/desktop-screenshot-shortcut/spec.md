## ADDED Requirements

### Requirement: User can configure a screenshot-answer shortcut
The desktop companion SHALL display a screenshot-answer shortcut setting beside screen capture controls and SHALL persist the selected preset across restarts.

#### Scenario: User selects an available shortcut
- **WHEN** the user selects a supported shortcut preset
- **THEN** the companion registers it globally, persists it locally, and displays that it is active

#### Scenario: User disables the shortcut
- **WHEN** the user selects the disabled option
- **THEN** the companion unregisters the previous shortcut and does not trigger screenshot answers from keyboard input

#### Scenario: Shortcut is already occupied
- **WHEN** the operating system rejects the selected shortcut because another application owns it
- **THEN** the companion preserves the previous working shortcut and displays an actionable conflict message

### Requirement: Shortcut capture requires an active live binding
The system MUST validate the invoking desktop device against the authoritative active capture binding before capturing the screen.

#### Scenario: Current device is bound to a live interview
- **WHEN** the user presses the active shortcut
- **THEN** the system creates one screenshot-answer request for that live session and captures the selected full screen

#### Scenario: Device has no live interview
- **WHEN** the shortcut is pressed while the device is unbound, preparing, stale, or ended
- **THEN** the system does not capture or upload any screen content and informs the user that no live interview is connected

### Requirement: Shortcut reuses the existing screenshot-answer pipeline
The system SHALL process shortcut screenshots through the existing capture, validation, upload, vision-answer, billing, and failure lifecycle.

#### Scenario: Shortcut answer completes
- **WHEN** the assistant captures and uploads a valid screen image
- **THEN** the existing Screenshot Answer Service generates the answer under the current session without using RAG

#### Scenario: Capture or upload fails
- **WHEN** screen permission, capture, upload, or model processing fails
- **THEN** the existing request is marked failed and the assistant displays the failure without silently retrying another capture

### Requirement: Live page receives shortcut-generated answers
The web live interview page SHALL merge completed shortcut-generated screenshot answers for the current session into the existing answer workspace.

#### Scenario: Shortcut task completes while live page is open
- **WHEN** a shortcut-generated screenshot task completes for the current session
- **THEN** the live page displays it once as a screenshot answer without replacing or duplicating unrelated answers

#### Scenario: User leaves the live page
- **WHEN** the current live page is hidden, replaced, or unmounted
- **THEN** shortcut answer synchronization stops and does not continue polling from an inactive page

### Requirement: Repeated shortcut presses are bounded
The desktop companion MUST prevent overlapping shortcut-triggered capture requests from the same device.

#### Scenario: User presses shortcut repeatedly
- **WHEN** a shortcut capture is already being created or processed
- **THEN** subsequent presses are ignored with a busy notice and do not create additional billable tasks
