## ADDED Requirements

### Requirement: Recover only the current valid microphone lifecycle
Mock capture SHALL become capturing only after its current context runs. A bounded resume failure, active context interruption or ended input SHALL fence PCM and release current resources with an explicit retry path. Silence MUST NOT be interpreted as OS denial. Old sockets, epochs, audio contexts, timers and late media promises MUST NOT affect replacement work. Existing pause/end/capture-null, backoff and bounded buffers SHALL remain.

#### Scenario: Context resume never becomes running
- **WHEN** resume stalls or returns while the current context is suspended
- **THEN** capture is not reported healthy, resources are safely released and manual retry remains available without marking OS permission denied

#### Scenario: Current input ends or remains muted
- **WHEN** a current track ends or a temporary mute persists beyond the bounded grace period
- **THEN** current capture stops safely with a concise retry notice, while a transient mute followed by unmute does not falsely fail

#### Scenario: Old capture finishes after pause or replacement
- **WHEN** an old open/resume/close callback resolves after pause/end, connection replacement or a new epoch
- **THEN** no old PCM, state, failure or resource close affects the current capture and no capture is automatically restarted
