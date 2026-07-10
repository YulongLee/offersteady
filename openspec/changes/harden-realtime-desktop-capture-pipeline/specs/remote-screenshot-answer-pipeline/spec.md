## ADDED Requirements

### Requirement: Screenshot answer SHALL expose remote capture stages
The screenshot answer pipeline SHALL expose the stage of each remote capture request from web request creation through desktop claim, capture, upload, vision processing, and answer completion.

#### Scenario: Request created but desktop does not claim
- **WHEN** the web page creates a remote screenshot request and the desktop companion does not claim it within the configured interval
- **THEN** the web page SHALL show that the request is waiting for the desktop companion rather than a generic fetch failure

#### Scenario: Desktop capture fails
- **WHEN** the desktop companion claims a screenshot request but cannot capture the selected screen
- **THEN** the backend SHALL store the desktop failure message and the web page SHALL display that message with retry and dismiss actions

### Requirement: Screenshot answer SHALL verify desktop binding before request creation
The web page SHALL create a remote screenshot request only when the current live session has an active desktop binding with matching device id and manual code.

#### Scenario: No active desktop binding
- **WHEN** the user clicks screenshot answer without an active desktop binding for the current session
- **THEN** the web page SHALL show a local diagnostic explaining that the desktop assistant must be connected first

### Requirement: Screenshot answer diagnostics SHALL avoid storing sensitive screenshot content
The system SHALL NOT store raw screenshot images in diagnostic reports; diagnostics may store request id, stage, image dimensions, content type, timing, and error code.

#### Scenario: Upload succeeds
- **WHEN** the desktop companion uploads a captured screenshot for answer generation
- **THEN** diagnostic output SHALL include upload success metadata without embedding the image data

### Requirement: Screenshot answer SHALL complete through vision and answer models
The screenshot answer pipeline SHALL only mark a request completed when the backend has created an answer task from the uploaded image and returned the answer to the web page.

#### Scenario: Vision model fails
- **WHEN** screenshot upload succeeds but the vision model fails
- **THEN** the request SHALL be marked failed with a vision-stage error and the web page SHALL not display a fabricated answer
