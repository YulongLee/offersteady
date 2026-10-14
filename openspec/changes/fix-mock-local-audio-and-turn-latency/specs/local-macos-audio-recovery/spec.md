## ADDED Requirements

### Requirement: Local Mac builds carry microphone capture authorization
The local Mac test application and its capture-capable helpers SHALL carry the audio-input entitlement required by their hardened-runtime signatures. Build verification SHALL reject a bundle missing that entitlement and SHALL identify the local build version.

#### Scenario: A helper misses microphone signing permission
- **WHEN** the main application has audio-input permission but a capture helper does not
- **THEN** artifact verification fails and the bundle is not reported as ready

#### Scenario: The local artifact is correctly signed
- **WHEN** the local artifact is compiled with the approved fix
- **THEN** its main and capture helper signatures contain audio-input permission and its local version is distinguishable from the installed build

#### Scenario: User tests the client against existing CN services
- **WHEN** a second CN-connected client test artifact is compiled on the same tested code
- **THEN** it uses the existing CN service defaults without a loopback override, retains required capture signing permissions, and does not deploy the pending backend optimizations

### Requirement: Microphone startup failures remain actionable
The companion SHALL retain an actionable microphone startup failure without replacing it with a generic reconnect message, SHALL avoid repeated permission-denied capture attempts, and SHALL preserve stopping and explicit recovery. Periodic registration SHALL not discard the companion's supported mock protocol capabilities.

#### Scenario: System rejects microphone acquisition
- **WHEN** microphone opening fails because access is denied
- **THEN** no audio is uploaded, the specific user-facing error remains visible, and automatic reconnect does not repeatedly reopen the microphone

#### Scenario: Device heartbeat refreshes capabilities
- **WHEN** the main process refreshes device registration
- **THEN** supported mock capabilities remain available without claiming an unverified microphone permission as granted
