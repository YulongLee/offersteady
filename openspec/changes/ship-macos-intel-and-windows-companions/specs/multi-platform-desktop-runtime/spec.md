## ADDED Requirements

### Requirement: Intel Mac runtime is architecture-correct
The system SHALL package an x64 Electron runtime and x64 macOS capture helper for the macOS Intel release.

#### Scenario: Inspect Intel package architecture
- **WHEN** a maintainer builds the macOS Intel target
- **THEN** the packaged Electron executable and native capture helper report x86_64 architecture

### Requirement: Windows companion supports the core interview journey
The Windows x64 companion SHALL use the existing device-pairing protocol and SHALL support microphone capture, computer-output loopback capture, screen capture, screenshot shortcuts, and online interview navigation.

#### Scenario: Use Windows companion in a live interview
- **WHEN** a Windows 10/11 x64 user pairs the companion and starts an interview
- **THEN** the companion publishes available candidate and interviewer audio channels and can submit a shortcut-triggered screenshot through the existing backend protocol

#### Scenario: Open the bound interview from the companion
- **WHEN** the companion has an authoritative active binding and the user selects "进入当前面试"
- **THEN** the system opens the bound session's live route and, if authentication is required, returns to that route after login

### Requirement: Platform diagnostics are truthful
The companion SHALL describe permissions and unavailable capture sources using instructions for the current operating system and SHALL NOT report an unavailable source as ready.

#### Scenario: Windows computer-output capture is unavailable
- **WHEN** Windows does not return a loopback audio track
- **THEN** the companion reports that computer-output capture is unavailable while keeping microphone, manual input, and screenshot paths usable

### Requirement: Sensitive captures remain transient
The multi-platform companion MUST keep raw audio and screen-preview data in memory and MUST NOT add local persistence of those captures.

#### Scenario: Companion session ends
- **WHEN** the user exits or disconnects a live interview
- **THEN** active media tracks are stopped without writing raw audio or screen recordings to local storage
