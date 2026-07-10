## ADDED Requirements

### Requirement: macOS capture runtime MUST provide real microphone frames
The desktop companion SHALL use a macOS capture runtime to capture the selected microphone or headset input and emit measurable audio levels and PCM frames.

#### Scenario: User speaks into the selected microphone
- **WHEN** the user speaks into the selected microphone during companion self-check or live interview
- **THEN** the capture runtime emits changing level events and PCM audio frames for role “我”

#### Scenario: Microphone permission is missing
- **WHEN** macOS microphone permission is denied or unavailable
- **THEN** the capture runtime emits `permission-required` or `capture-error` and the companion does not show microphone capture as ready

### Requirement: macOS capture runtime MUST capture computer output audio
The desktop companion SHALL capture the computer output audio that the candidate hears from meeting software, WeChat, browser playback or other desktop applications.

#### Scenario: Computer playback is audible
- **WHEN** supported macOS capture runtime is active and the computer plays WeChat, meeting or browser audio
- **THEN** the runtime emits changing level events and PCM audio frames for role “面试官”

#### Scenario: Computer output cannot be captured
- **WHEN** the runtime cannot capture computer output due to unsupported macOS version, permission or missing native capability
- **THEN** the companion reports the output source as unavailable and does not show a successful interviewer-audio state

### Requirement: macOS capture runtime MUST provide selected-display screen frames
The desktop companion SHALL capture preview frames from the selected display through the same runtime path that will support screenshot answering.

#### Scenario: Selected display is captured
- **WHEN** the user selects a display and grants screen recording permission
- **THEN** the runtime emits at least one screen frame for that display and the companion marks screen capture as ready

#### Scenario: Screen capture permission is missing
- **WHEN** macOS screen recording permission is denied or not yet granted
- **THEN** the companion reports screen capture as permission-required and does not display a fake preview

### Requirement: Native runtime MUST not persist raw media by default
The capture runtime MUST keep audio and screen frames transient and MUST NOT write local recordings, screenshots or screen videos under default settings.

#### Scenario: Diagnostic report is generated
- **WHEN** diagnostics are exported after a capture attempt
- **THEN** the report includes source states, frame counters and errors but excludes raw audio samples and screen image data
