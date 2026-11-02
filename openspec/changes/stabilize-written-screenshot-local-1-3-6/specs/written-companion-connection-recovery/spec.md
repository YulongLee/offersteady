## ADDED Requirements

### Requirement: Bound heartbeat work and preserve current recovery intent
The companion SHALL bound the complete registration operation, coalesce concurrent recovery triggers and fence late results. Normal heartbeats SHALL remain at a 15-second interval. Resume, foreground or network recovery SHALL refresh current readiness without starting capture, rebinding another session or increasing continuous polling. Diagnostics MUST exclude credentials and user content.

#### Scenario: A registration hangs or returns late
- **WHEN** an operation exceeds its deadline and a later recovery succeeds
- **THEN** the old result cannot overwrite current state or keep the coordinator busy indefinitely

#### Scenario: Multiple recovery signals arrive
- **WHEN** resume and foreground signals overlap
- **THEN** they cause bounded merged work and never duplicate registration, capture or billing

### Requirement: Restore only a verified current written connection
Recovery SHALL revalidate the existing live written binding before reopening suspended screenshot delivery. Active written sessions SHALL hold a temporary application-suspension blocker, released when the binding becomes inactive, the session ends or the app quits. OS recording and user permission indicators SHALL remain unchanged.

#### Scenario: Heartbeat recovers but binding is ended or changed
- **WHEN** network readiness improves after a binding was replaced or ended
- **THEN** no screenshot stream, stale queue or capture is resurrected

#### Scenario: The user hides a valid written companion
- **WHEN** a verified live written binding remains active while its window is hidden
- **THEN** temporary app-suspension protection persists without showing the window, locking the display or starting audio
