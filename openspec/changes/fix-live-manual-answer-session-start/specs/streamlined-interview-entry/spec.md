## ADDED Requirements

### Requirement: Starting an interview MUST activate the backend session before entering live workspace
The system SHALL call the backend Interview Session start API and receive a successful live session response before navigating from the preparation page to the live interview workspace.

#### Scenario: User starts an interview from the preparation page
- **WHEN** the user has confirmed the material list and clicks "开始面试 →"
- **THEN** the frontend MUST call the backend start-session endpoint for the current Interview Session
- **AND** the frontend MUST enter the live workspace only after the backend confirms the session is live

#### Scenario: Backend start fails
- **WHEN** the backend start-session request fails
- **THEN** the user MUST remain on the preparation page
- **AND** the page MUST preserve the current material selection
- **AND** the page MUST show the real failure reason or a clear retryable error message

#### Scenario: User clicks start repeatedly
- **WHEN** a start-session request is already in flight
- **THEN** the frontend MUST prevent duplicate start requests for the same click flow

### Requirement: Manual answer failures MUST show the actual answer failure cause
The system SHALL display a manual-answer failure message based on backend or transport error details and MUST NOT always attribute the failure to points, membership, or billing.

#### Scenario: Backend rejects answer because session is not live
- **WHEN** the backend rejects a manual answer request because the session is not live
- **THEN** the frontend MUST show a message that explains the interview session has not started or must be re-entered
- **AND** the frontend MUST NOT show "当前任务未启动，请检查积分或会员权益" as the primary explanation

#### Scenario: Backend returns a model or validation error
- **WHEN** the backend returns a structured error message for a manual answer request
- **THEN** the live page MUST show that message in the answer failure state or global alert

#### Scenario: Billing is not the error source
- **WHEN** the failure is caused by session state, authentication, model, network, or backend validation
- **THEN** the frontend MUST NOT direct the user primarily to the billing page

### Requirement: Live answer entry MUST remain visually unchanged
The system SHALL preserve the approved live interview page structure while fixing session start and error handling behavior.

#### Scenario: Session starts successfully
- **WHEN** the backend confirms the session is live and the user enters the live workspace
- **THEN** the existing live page layout, compact question bar, and "回答问题" action placement MUST remain unchanged

#### Scenario: User answers manually after session start
- **WHEN** the user enters a question and clicks "回答问题" after the backend session is live
- **THEN** the request MUST be eligible for Chat Service processing without failing due to a stale preparing session state
