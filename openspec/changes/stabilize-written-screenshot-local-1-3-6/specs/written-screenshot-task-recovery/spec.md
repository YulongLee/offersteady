## ADDED Requirements

### Requirement: Keep explicit pending requests while busy
A written screenshot processor SHALL serialize one active and at most four pending user-requested captures, deduplicate requests and retain bounded FIFO order. Queue overflow SHALL have explicit recoverable feedback rather than silent success. Ordinary and mock workflows SHALL preserve their existing semantics.

#### Scenario: A second request arrives during capture or upload
- **WHEN** a current request is busy and another valid request arrives
- **THEN** the second request is queued or explicitly rejected and is not silently lost after the first finishes

### Requirement: Fence capture upload and cancellation lifecycles
The processor SHALL enforce bounded capture/upload/report deadlines, validate the current binding and session-scoped server request status before capturing and uploading, and discard cancelled, replaced or late results. Lock ownership SHALL prevent stale operations from releasing a newer lock. Ambiguous upload outcomes MUST NOT cause blind duplicate uploads or model/billing work.

#### Scenario: Capture times out and later resolves
- **WHEN** a timed-out OS capture resolves after a new request starts
- **THEN** it neither uploads its old image nor releases the new request's lock

#### Scenario: Pending capture is cancelled or its session changes
- **WHEN** cancellation or binding replacement overtakes a queued request
- **THEN** it does not capture or upload on the new page, and a late 409 does not fail the current request

#### Scenario: An upload stalls
- **WHEN** uploading exceeds its deadline
- **THEN** it is classified as upload failure, current state is recovered safely and no automatic duplicate generation is sent

### Requirement: Preserve device scoped read authorization
The existing device next-request endpoint SHALL accept optional sessionId and requestId queries using its existing device credentials. The query SHALL match the current valid binding and request owner/session/device/code; mismatched records MUST NOT be returned. Without optional queries the existing behavior SHALL remain. Reads MUST NOT claim, mutate, bill or invoke models. Clients of an older server SHALL reject mismatched canonical responses without capturing another session.

#### Scenario: The same device has an older pending request
- **WHEN** a current written session queries its pending or specified request
- **THEN** the new server returns only matching current records and the helper rejects older-server responses belonging to another session

#### Scenario: A request has been cancelled
- **WHEN** the current device queries a matching cancelled request
- **THEN** its terminal state is returned read-only and the helper skips capture and upload
