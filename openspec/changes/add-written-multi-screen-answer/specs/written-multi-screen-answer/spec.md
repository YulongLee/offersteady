## ADDED Requirements

### Requirement: Written workspace offers an optional multi-screen switch
The written workspace SHALL show a keyboard-accessible “多屏回答” switch in its top action row, off on entry. When enabled it SHALL replace “截屏回答” with separate “截屏” and “回答” buttons, and show the ordered pending screenshot count and removal controls. Other session modes SHALL retain their existing controls.

#### Scenario: User enables the switch
- **WHEN** a user enables multi-screen answering in an active written session
- **THEN** the workspace shows two buttons, with Answer disabled until a screenshot is ready

#### Scenario: Switch is off or session is an interview
- **WHEN** the switch is off or the session is not written
- **THEN** single-screen capture-and-answer retains its existing behavior

### Requirement: Collection does not generate answers or charge usage
An explicit capture-only request SHALL capture the currently selected shared screen through the existing companion, temporarily register one image and return its capture identity, without invoking vision, creating answer history or reserving/settling answer usage. Missing capture-only fields SHALL preserve existing behavior. The UI SHALL serialize captures and use the backend image limit, currently four.

#### Scenario: User captures successive pages
- **WHEN** the user captures three successive views
- **THEN** three ordered pending items are shown with no generated answer or answer charge

#### Scenario: Capture fails or limit is reached
- **WHEN** capture fails or the maximum count is reached
- **THEN** existing pending items remain, failures are actionable and further capture is disabled at the limit

### Requirement: Batch answering is ordered and isolated
Answer SHALL submit the ordered capture-request identities as one asynchronous screenshot task using the existing provider gateway, streaming presentation and screenshot-answer billing rule. The server MUST validate ownership, active written-session scope, captured image availability, count, duplicates and already submitted requests before work. Repeated submission of the same ordered batch MUST return the same request without creating additional model or billing work. No Resume, JD or Knowledge context SHALL be used.

#### Scenario: User submits a batch
- **WHEN** the user answers using two ready captures
- **THEN** one task receives both original images in capture order, streams one AI suggestion and records one screenshot usage

#### Scenario: Submission is repeated or forged
- **WHEN** a request is repeated or includes another account/session's capture, duplicates, an expired capture, or an image already used by another batch
- **THEN** the repeated valid batch returns its original request and invalid input performs no model or billing work

### Requirement: Pending screenshots and requests have bounded lifetimes
The system MUST release unused captures when removed, when switching off, leaving or ending the workspace, or when the page is replaced. Existing short-lived in-memory expiry SHALL cover interrupted clients. It MUST NOT persist image bytes in browser storage or diagnostic logs. In-flight callbacks after cancellation MUST NOT revive a removed image or add an answer after cancellation. Submission failures SHALL indicate whether recapture is necessary instead of silently replaying consumed images.

#### Scenario: User clears or switches off
- **WHEN** the user removes a capture or disables multi-screen mode
- **THEN** pending captures are released and cannot later be submitted

#### Scenario: Cancel races with desktop upload
- **WHEN** the user cancels while upload or generation is in flight
- **THEN** late results do not restore pending captures or revive cancelled work, and completed temporary image storage is released

#### Scenario: An image expires before submission
- **WHEN** an image's existing temporary lifetime has elapsed
- **THEN** submission reports that it must be captured again and does not charge or call a model

### Requirement: Local validation preserves the sealed production baseline
Implementation SHALL start from `release-cn-20261019.1` and use only synthetic inputs in tests. It SHALL verify capture-only no-side-effects, image order, one-task usage, duplicate/concurrent submission, cleanup, errors, and existing single-screen and other session controls. This change SHALL remain local until separately authorized for production release.

#### Scenario: Local implementation is complete
- **WHEN** the new mode is reviewed
- **THEN** a local preview and documented checks are available, with no production restart, real-user capture or model test

### Requirement: Authorized CN release preserves other production capabilities
After the user's explicit CN deployment authorization, the release SHALL change only the CN Backend and Web images, derived from their freshly verified actual running images. It MUST preserve all unrelated source, static files, routes, effective settings and other components, with exact intended deltas recorded. Active user work and ongoing billing or processing MUST defer every cutover; no session may be stopped or protection relaxed to enable release. Candidate validation SHALL use synthetic inputs only, and failed cutover SHALL use the same ownership and idle protection before restoring pinned prior images.

#### Scenario: Fresh runtime matches the approved development base
- **WHEN** preparing the authorized CN release
- **THEN** the operator verifies the complete actual Backend/Web inventories and builds only the six approved Backend source deltas and a minimal Web overlay, retaining the frozen unrelated files

#### Scenario: User work is active
- **WHEN** any protected work, financial state or Backend connection gate reports busy or unreadable
- **THEN** release does not cut over or terminate work; it defers or stops for diagnosis

#### Scenario: Production validation completes
- **WHEN** the fixed candidate images are active
- **THEN** independent verification checks their ownership, exact source/static/schema/settings deltas, protected existing routes, anonymous guards and short aggregate error observation without exposing user content
