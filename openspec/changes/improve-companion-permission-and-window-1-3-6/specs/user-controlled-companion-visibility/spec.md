## ADDED Requirements

### Requirement: Hide and restore application UI through explicit user intent
On explicit hide, the companion SHALL hide its main window and Dock/taskbar entry, while retaining the same tray/menu icon instance with a fixed-size fully transparent image and clickable bounds while retaining the same process and capture connection. Left-clicking the transparent tray/menu slot, opening the application again or using an available restore shortcut SHALL restore its existing window and entry points without allocating duplicate capture. Fully quitting and relaunching SHALL start visible. Website status/stop controls and OS recording/permission indicators SHALL remain available and unmodified.

#### Scenario: User hides during a valid connection
- **WHEN** the user clicks hide
- **THEN** the window and Dock/taskbar disappear, the original icon slot stays present and clickable with fully transparent pixels, and capture/binding/heartbeat state remains unchanged

#### Scenario: User restores or the shortcut is occupied
- **WHEN** the user left-clicks the original transparent icon slot, opens the application again or presses an available restore shortcut
- **THEN** the same instance immediately restores its window, normal tray image and Dock/taskbar, and shortcut conflict cannot remove the application-reopen recovery path

### Requirement: Respect visibility intent across asynchronous lifecycle events
All ready-to-show, renderer recovery and delayed Dock operations SHALL respect the latest visibility intent. Hidden renderer recovery MUST NOT unexpectedly reveal the window. Missing windows SHALL be recoverable through explicit user reopening. Visibility SHALL NOT implicitly start/stop capture or bypass OS permissions.

#### Scenario: Renderer recovers while hidden
- **WHEN** a hidden window must be recreated after a renderer failure
- **THEN** its ready event keeps it hidden until explicit restore

#### Scenario: Hide and restore race
- **WHEN** rapid hide/restore or an older delayed Dock operation settles
- **THEN** the latest intent wins and no stale callback hides the restored UI

### Requirement: Preserve a transparent recovery target
Hide MUST NOT destroy the Tray or replace it with an empty/null image. The transparent image SHALL reserve nonzero bounds matching the visible icon footprint. Left-click SHALL restore directly without an extra menu selection; the original status/open/stop menu SHALL remain reachable by right-click. Restoration SHALL NOT allocate duplicate capture or restart audio.

#### Scenario: Transparent icon is clicked
- **WHEN** the user clicks the original tray/menu icon position after hiding
- **THEN** the existing window and normal icon are restored, the same Tray object survives and capture state is untouched

#### Scenario: Menu remains usable while hidden
- **WHEN** the user right-clicks the retained transparent slot
- **THEN** the existing open/stop menu remains usable without automatic capture changes
