## ADDED Requirements

### Requirement: Desktop companion SHALL embed the Web interview workspace
The desktop companion SHALL provide an embedded Web workspace area that can open the current OfferSteady Web application while keeping desktop capture status visible.

#### Scenario: Embedded workspace opens
- **WHEN** the desktop companion launches with a configured Web URL
- **THEN** it loads the OfferSteady Web workspace in the desktop shell and shows capture status controls outside or alongside the embedded page

#### Scenario: Embedded workspace cannot load
- **WHEN** the configured Web URL is unavailable
- **THEN** the companion shows a clear error and provides an action to retry or open the workspace in the external browser

### Requirement: Embedded Web workspace MUST use backend APIs rather than desktop secrets
The embedded Web page MUST authenticate and call backend APIs through the same browser-safe mechanisms as the normal Web app and MUST NOT receive server API keys, ASR keys, or desktop device credentials.

#### Scenario: Web page requests data
- **WHEN** the embedded Web app loads interview, material, answer, billing, or transcript state
- **THEN** it uses normal backend API requests and does not access desktop-only credentials

### Requirement: Desktop shell MUST synchronize capture state into embedded workspace
The desktop shell SHALL publish capture and source status through backend session state or a safe local bridge so the embedded workspace can show whether monitoring is connected, ready, capturing, paused, degraded, or failed.

#### Scenario: Capture starts in desktop shell
- **WHEN** the user starts capture from the desktop companion
- **THEN** the embedded workspace updates its visible capture/monitoring status for the current interview session

#### Scenario: Capture fails
- **WHEN** the companion reports permission, source, network, or ASR failure
- **THEN** the embedded workspace shows a degraded or error state and keeps manual question input available

### Requirement: Desktop package MUST expose a local development download entry
The product SHALL expose a macOS Apple Silicon local development package entry that users can download or open from the current development machine.

#### Scenario: User opens download page on development Mac
- **WHEN** the Web device/download page loads while a local macOS arm64 artifact exists
- **THEN** it shows the artifact as available for the current development machine with architecture, version, capability, and local/development status

#### Scenario: Local artifact is missing
- **WHEN** the Web device/download page loads before a local artifact has been built
- **THEN** it shows build instructions or an unavailable state instead of a fake working download

### Requirement: Embedded workspace MUST preserve approved live-page layout
The embedded desktop workspace MUST keep the approved live interview page structure and MUST NOT reintroduce material rails, role correction, or a third role UI.

#### Scenario: User enters live interview inside desktop app
- **WHEN** the embedded Web workspace opens an active interview
- **THEN** it shows the existing conversation and answer workspace with “面试官” and “我” roles only
