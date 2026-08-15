## ADDED Requirements

### Requirement: Successful desktop screenshot remains locked until cancellation
The desktop companion MUST keep a single authoritative screenshot lock after a valid screen image has been captured and MUST release it only when the user explicitly cancels the current screenshot or the application exits.

#### Scenario: First screenshot succeeds
- **WHEN** a manual preview, remote web request, or global shortcut captures a valid screen image
- **THEN** the desktop companion marks the screenshot session as locked
- **AND** displays an action to cancel the current screenshot

#### Scenario: Capture fails before producing an image
- **WHEN** permission, source selection, or screen capture fails without a valid image
- **THEN** the system releases the lock automatically
- **AND** the user can retry without restarting the application

### Requirement: Locked screenshot blocks every desktop capture entry
The desktop companion MUST reject additional manual previews, remote captures, and shortcut-triggered screenshot requests while the screenshot lock is active.

#### Scenario: User presses the shortcut while locked
- **WHEN** the screenshot lock is active and the user presses the configured global shortcut
- **THEN** the system does not create another screenshot-answer request
- **AND** informs the user to cancel the current screenshot first

#### Scenario: User clicks preview while locked
- **WHEN** the screenshot lock is active
- **THEN** the preview control and screen-source selector are disabled
- **AND** no second screen capture is performed

### Requirement: User cancellation enables the next screenshot
The desktop companion SHALL provide a visible cancellation action that releases the screenshot lock without claiming to cancel an already submitted server answer.

#### Scenario: User cancels the current screenshot
- **WHEN** the user activates “取消当前截屏”
- **THEN** the local preview stream is stopped and the authoritative lock is released
- **AND** the preview control, screen selector, and global shortcut can start a new screenshot
