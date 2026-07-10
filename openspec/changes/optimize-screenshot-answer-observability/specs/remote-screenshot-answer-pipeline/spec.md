## ADDED Requirements

### Requirement: Screenshot answer SHALL report stage progress
The remote screenshot answer pipeline SHALL expose user-visible progress stages from request creation through desktop claim, upload, vision generation, completion, failure, or cancellation.

#### Scenario: Upload returns before vision completion
- **WHEN** the desktop companion uploads a screenshot and the backend accepts it for background processing
- **THEN** the API SHALL return a processing state without waiting for the vision model to complete

#### Scenario: Web displays vision generation
- **WHEN** a screenshot request has been uploaded and the answer task is waiting for or running the vision model
- **THEN** the web page SHALL display a stage-specific message indicating that the answer is being generated

### Requirement: Screenshot answer SHALL record phase timing telemetry
The screenshot answer pipeline SHALL record metadata-only timing for each major phase of a screenshot answer request.

#### Scenario: Successful screenshot answer
- **WHEN** a screenshot answer completes successfully
- **THEN** the resulting task or request telemetry SHALL include timings for upload return, image optimization when available, OSS write, signed URL generation, vision model call, answer persistence, and total background processing

#### Scenario: Failed screenshot answer
- **WHEN** a screenshot answer fails during upload, OSS, signing, vision, or answer persistence
- **THEN** the telemetry SHALL include the failed phase and error code without storing raw screenshot content

### Requirement: Screenshot answer diagnostics SHALL remain metadata-only
Screenshot answer diagnostics SHALL NOT store raw screenshots, base64 image data, or screenshot-derived sensitive text.

#### Scenario: Performance report generated
- **WHEN** a local performance report is generated for a screenshot answer test
- **THEN** the report SHALL include request id, task id, stage, dimensions, byte counts, model name, timing, and error code only

### Requirement: Screenshot answer SHALL preserve full-screen capture workflow
The screenshot answer pipeline SHALL optimize full-screen screenshots automatically without requiring users to manually crop or select a question region.

#### Scenario: User triggers screenshot answer during full-screen interview
- **WHEN** the user triggers screenshot answer from the live interview page
- **THEN** the desktop companion SHALL capture the selected full screen and automatically compress it before upload

### Requirement: Screenshot answer SHALL be independent from personal materials
Screenshot answer generation SHALL NOT use resume, JD, or knowledge base RAG context.

#### Scenario: Screenshot answer with bound interview materials
- **WHEN** an interview session has resume, JD, or knowledge materials bound
- **THEN** screenshot answer SHALL generate from the screenshot and user instruction only, and telemetry SHALL show no RAG retrieval usage

### Requirement: Screenshot answer performance SHALL be locally reproducible
The project SHALL provide a local self-test path that runs a complete screenshot answer flow with a specified image and writes a phase-by-phase performance report.

#### Scenario: Developer runs screenshot performance test
- **WHEN** the developer runs the screenshot answer performance test with a local image path
- **THEN** the test SHALL create a report showing each phase duration and whether additional non-model optimization remains
