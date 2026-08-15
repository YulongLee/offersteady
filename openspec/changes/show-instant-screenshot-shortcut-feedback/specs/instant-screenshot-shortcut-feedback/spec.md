## ADDED Requirements

### Requirement: Accepted shortcut capture produces immediate web feedback
The system SHALL notify the active live web page through its existing realtime session stream after a desktop shortcut capture request has been accepted.

#### Scenario: Shortcut request is accepted
- **WHEN** the authorized desktop device creates a shortcut screenshot request for the active live session
- **THEN** the web page displays the same waiting screenshot dialog used by the screenshot button without waiting for the next history poll
- **AND** the notification identifies the authoritative capture request ID

#### Scenario: Shortcut request is rejected
- **WHEN** the shortcut is rejected because the device is unbound, the interview is not live, or another capture remains active
- **THEN** no accepted screenshot event is published and the web page does not display a false processing dialog

### Requirement: Shortcut feedback reconciles without duplicate work
The web page MUST reconcile realtime acceptance, polled progress, cancellation, and completion by authoritative capture request ID.

#### Scenario: Progress arrives after realtime acceptance
- **WHEN** low-frequency recovery synchronization returns progress for a request already announced through the realtime stream
- **THEN** the existing dialog advances to the authoritative stage without adding another capture request or duplicate answer

#### Scenario: Realtime stream is temporarily unavailable
- **WHEN** the active live page cannot receive the realtime acceptance event
- **THEN** the existing visible-page low-frequency synchronization can recover the request and its result
- **AND** the system does not increase idle database polling frequency
