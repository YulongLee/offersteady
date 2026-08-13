## ADDED Requirements

### Requirement: User SHALL be able to download an editable Word review

The review page SHALL provide a primary Word download action that creates one standards-compliant `.docx` file from the current owned interview review. The generated file MUST be locally generated and MUST be openable and editable by Microsoft Word, WPS, or another standards-compatible DOCX tool.

#### Scenario: Owner downloads a completed review
- **WHEN** the owner clicks “下载 Word” on an ended interview review
- **THEN** the browser downloads one `.docx` file without uploading a generated attachment to the server

### Requirement: Word review MUST preserve complete available review content

The Word document MUST include session metadata, chronological final interviewer and candidate transcripts, and every available question with its AI answer suggestion. It MUST NOT truncate content based on simple or detailed answer mode.

#### Scenario: Review contains long questions and answers
- **WHEN** the review includes multi-paragraph or long-form transcript and AI answer content
- **THEN** the generated Word document contains the complete available text and allows it to flow across pages

#### Scenario: Historical content is unavailable
- **WHEN** a review has no persisted transcript or no AI answer records
- **THEN** the corresponding document section truthfully identifies that no record is available without inventing content

### Requirement: Word review MUST distinguish transcript from AI advice

The Word document MUST place actual speech transcripts and AI answer suggestions in separately titled sections. It MUST label interviewer and candidate transcript entries by role and MUST describe generated answers as AI suggestions rather than words spoken by the candidate.

#### Scenario: Review contains transcript and suggestions
- **WHEN** both actual speech transcripts and generated answer suggestions are exported
- **THEN** a reader can distinguish the “真实对话记录” section from the “问题与 AI 回答建议” section through headings and labels

### Requirement: Word export MUST remain privacy bounded

The system MUST generate the Word file only after an explicit user action in the authenticated review page. It MUST NOT include raw audio, model prompts, provider responses, or another account's content, and MUST NOT persist the generated document on the server.

#### Scenario: Word document is generated
- **WHEN** an authorized user downloads a review
- **THEN** generation occurs in the browser from the already authorized review snapshot and no server-side export attachment is created

### Requirement: Word generation SHALL expose usable progress and failure states

The review page SHALL prevent duplicate generation while the file is being built and SHALL show a recoverable error if document generation or browser download fails.

#### Scenario: Generation is in progress
- **WHEN** the DOCX generator has not finished
- **THEN** the action indicates that Word is being generated and cannot be triggered repeatedly

#### Scenario: Browser download fails
- **WHEN** the browser cannot generate or download the DOCX file
- **THEN** the page displays a clear retryable failure message without losing the visible review
