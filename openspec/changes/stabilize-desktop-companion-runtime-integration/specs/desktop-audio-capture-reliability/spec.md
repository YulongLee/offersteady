## ADDED Requirements

### Requirement: Microphone input MUST produce measurable local signal before publishing success
The companion SHALL verify the selected microphone or headset input by opening the selected device, observing a live audio track, measuring signal level, and producing PCM frames.

#### Scenario: User speaks into selected headset
- **WHEN** the user selects a headset microphone and speaks during an active test or interview
- **THEN** the companion displays changing level diagnostics and reports microphone frames produced for role “我”

#### Scenario: Selected microphone cannot be opened
- **WHEN** the selected microphone device is missing, denied, busy, or unreadable
- **THEN** the companion reports the specific device failure and does not create a microphone publisher

### Requirement: System output audio MUST represent computer playback heard by the candidate
The companion SHALL treat system output audio as the audio that the candidate hears from meeting software, WeChat, browser playback, or other desktop applications, and SHALL route it to role “面试官”.

#### Scenario: Computer plays interviewer audio
- **WHEN** a supported system output adapter is active and the computer plays meeting or WeChat audio
- **THEN** the companion displays changing system-output level diagnostics and publishes frames with role “面试官”

#### Scenario: Platform cannot capture output audio
- **WHEN** the current macOS/Electron runtime cannot provide a real system-output audio stream
- **THEN** the companion reports `adapter-required` or `unsupported` and does not show the system-output source as successfully capturing

### Requirement: Audio publishers MUST acknowledge backend receipt
The companion SHALL publish microphone and system-output frames to backend Realtime Speech and track backend receipt separately for each source.

#### Scenario: Backend receives microphone frames
- **WHEN** microphone PCM frames are sent through the realtime publisher
- **THEN** backend runtime status records recent microphone frame count and last frame time

#### Scenario: Backend receives system-output frames
- **WHEN** system-output PCM frames are sent through the realtime publisher
- **THEN** backend runtime status records recent system-output frame count and last frame time

### Requirement: ASR transcripts MUST preserve source role
The backend SHALL convert accepted audio frames into transcript events that preserve source kind and visible role.

#### Scenario: Microphone ASR result arrives
- **WHEN** ASR returns text for microphone frames
- **THEN** the transcript event is stored and returned to Web as role “我”

#### Scenario: System-output ASR result arrives
- **WHEN** ASR returns text for system-output frames
- **THEN** the transcript event is stored and returned to Web as role “面试官”
