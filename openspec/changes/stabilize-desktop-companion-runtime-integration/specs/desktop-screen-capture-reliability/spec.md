## ADDED Requirements

### Requirement: Screen capture MUST use the selected display as the single source
The companion SHALL use the selected display for permission checks, preview and subsequent screenshot-answer capture.

#### Scenario: User selects display one
- **WHEN** the user selects display one in the companion
- **THEN** preview frames and later screenshot capture use that same display source

#### Scenario: Selected display disappears
- **WHEN** the selected display is disconnected or no longer available
- **THEN** the companion reports the screen source as unavailable and requires a new valid display selection before capture succeeds

### Requirement: Screen preview MUST prove capture works
The companion SHALL only mark screen capture as ready after it can obtain at least one preview frame from the selected display.

#### Scenario: Preview frame is received
- **WHEN** the selected display grants capture permission and a preview frame is produced
- **THEN** the companion reports screen capture as ready

#### Scenario: Preview frame cannot be received
- **WHEN** permission is missing, the source is unavailable, or no frame is produced
- **THEN** the companion reports screen capture as failed or permission-required and does not claim screenshot capture readiness

### Requirement: Screen capture diagnostics MUST not store screen content
The system MUST report screen capture status without storing preview frames or screenshots in diagnostics by default.

#### Scenario: Screen capture diagnostic report is generated
- **WHEN** diagnostics are exported after testing screen capture
- **THEN** the report includes source id, display label, permission state, frame count and error code, but not screen image data
