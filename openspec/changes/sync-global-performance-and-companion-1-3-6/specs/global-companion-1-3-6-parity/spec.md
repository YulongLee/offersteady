## ADDED Requirements

### Requirement: Global companion retains independent identity and presentation
Global companion1.3.6 SHALL retain its stable Global application/bundle identity, data directory, protocol, Electron version, supported operating systems and production offersteady.com HTTPS endpoints. It SHALL preserve the approved appearance and English interface/permission/error presentation, exclude CN/local overrides, compiled tests and server credentials, and preserve existing supported languages and Global membership rules.

#### Scenario: A Global user installs the new helper
- **WHEN** the user exits the preceding helper and installs the matching platform package
- **THEN** the application reports1.3.6, retains its Global identity and existing device state, uses Global production endpoints and exposes no new standalone recheck control or permanent declaration block

#### Scenario: A newly introduced capture or connection error is shown
- **WHEN** a Global user encounters an error added by the1.3.6 recovery paths
- **THEN** the visible message is correctly localized to Global English instead of exposing newly introduced Chinese UI text

### Requirement: Permission and microphone recovery remain truthful and lifecycle scoped
The Global helper SHALL distinguish pending/unknown, granted, denied and unavailable permission states, apply current late authorization and coalesce changed capability registration without increasing periodic polling. Mock capture SHALL require only its microphone inputs, verify the current context is running, detect current track/context interruption, release old resources and expose the existing explicit retry. Timeout or silence MUST NOT imply OS denial, Windows MUST NOT fake permission, and obsolete callbacks MUST NOT resume paused/ended capture or affect replacements.

#### Scenario: Authorization finishes after a UI waiting interval
- **WHEN** the current OS request resolves late
- **THEN** it updates current permission once without false denial or duplicate permission requests, while obsolete results remain fenced

#### Scenario: An old microphone operation finishes after replacement
- **WHEN** an old audio context, track, socket or media promise finishes after pause, end or a new epoch
- **THEN** it sends no obsolete PCM and cannot alter or close the replacement capture

### Requirement: Written recovery is bounded and current session specific
Global helper1.3.6 SHALL preserve the normal heartbeat interval while bounding registration and merging resume/foreground/network recovery. Screenshot delivery SHALL reopen only after current live written binding verification. Explicit screenshot requests SHALL use bounded FIFO/deduplication and capture/upload/report deadlines, preserve lock ownership, discard cancelled/expired/cross-session results and avoid blind upload retry or duplicate generation/billing. Active written sessions may hold a scoped temporary application-suspension blocker, released on binding loss/end/quit without locking the display or starting audio.

#### Scenario: Another valid request arrives during capture
- **WHEN** a current screenshot is busy
- **THEN** the second explicit request is queued within the existing bounded capacity or clearly rejected, never silently lost as a fake success

#### Scenario: Old capture or upload settles after timeout or session replacement
- **WHEN** a cancelled, expired or obsolete operation returns late
- **THEN** it cannot upload another session's image, release a newer lock, overwrite current feedback or trigger duplicate billing/model work

#### Scenario: Connectivity returns after a session ended
- **WHEN** a heartbeat or network recovery succeeds for an ended or replaced binding
- **THEN** no old screenshot queue, capture or audio session is automatically resurrected

### Requirement: Explicit hiding retains a clickable recovery target
Explicit hide SHALL conceal the helper main window and Dock/taskbar entry while retaining the same nonempty fixed-size transparent tray/menu target. Left click, application reopen or an available restore shortcut SHALL restore the same window and normal icon without duplicate capture. Existing right-click open/stop access, website stop controls and OS privacy indicators SHALL remain. A fresh launch SHALL begin visible and delayed lifecycle work SHALL respect the latest user visibility intent.

#### Scenario: User hides and clicks the original icon slot
- **WHEN** the user explicitly hides a connected helper and later left-clicks the retained transparent target
- **THEN** the same helper/window is restored with unchanged binding/capture ownership and no additional audio session

#### Scenario: Renderer recovers while hidden
- **WHEN** delayed window or renderer recovery completes after a hide/restore change
- **THEN** the latest explicit visibility intent wins and recovery does not unexpectedly reveal or hide the window

### Requirement: All three official artifacts match frozen tested Global inputs
The release SHALL prepare macOS arm64, macOS x64 and Windows x64 packages from the same approved Global source, freeze each architecture before another build changes shared dist/native, and verify exact packaged runtime and architecture. Both Mac App and DMG SHALL pass actual Developer ID, audio-input entitlement, notarization, stapler and Gatekeeper checks. Windows SHALL pass NSIS outer/inner and real x64 payload checks with truthful unsigned status. Physical audio/permission/network acceptance SHALL not be claimed from structural checks.

#### Scenario: A production Mac candidate is only a local test package
- **WHEN** a candidate lacks verified Global signing, App/DMG notarization or payload proof
- **THEN** it cannot become the official Global download by renaming or metadata edits

#### Scenario: A platform differs from frozen Global source or payload
- **WHEN** any packaged runtime or native architecture does not match its verified frozen input
- **THEN** publication stops before the public version changes
