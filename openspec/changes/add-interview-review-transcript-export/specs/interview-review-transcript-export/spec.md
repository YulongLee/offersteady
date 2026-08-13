## ADDED Requirements

### Requirement: Review SHALL include both interview participants' final transcripts

The system SHALL show final persisted speech transcripts for the interviewer and candidate in chronological order after an interview ends. It MUST label `system` speech as “面试官” and `microphone` speech as “我”, and MUST NOT include interim transcript revisions.

#### Scenario: Both roles spoke during the interview
- **WHEN** the owner opens the ended interview review
- **THEN** the review displays the final interviewer and candidate transcript entries in their original chronological order

#### Scenario: Historical transcript is unavailable
- **WHEN** an ended interview has no persisted final transcript entries
- **THEN** the review displays a truthful empty state while keeping available question and AI-answer records usable

### Requirement: Review SHALL distinguish actual transcript from AI advice

The system SHALL present speech transcripts and AI answer suggestions in separate labelled sections. It MUST NOT describe AI suggestions as words actually spoken by the candidate.

#### Scenario: A question has AI advice and candidate speech
- **WHEN** the review contains both data types
- **THEN** “真实对话记录” shows role-labelled speech and “问题与 AI 回答建议” shows generated guidance separately

### Requirement: Review data access MUST enforce session ownership

The backend MUST authorize review reads against the current session owner and MUST NOT return another user's transcript or answer data.

#### Scenario: Another user requests the review
- **WHEN** an authenticated user requests a session owned by another user
- **THEN** the backend rejects the request without returning transcript content

### Requirement: User SHALL be able to download a local Markdown review

The review page SHALL provide an explicit download action that generates a UTF-8 Markdown file locally in the browser. The file SHALL include session metadata, chronological role-labelled transcripts, and available questions with AI answer suggestions.

#### Scenario: User downloads a complete review
- **WHEN** the owner clicks “下载复盘”
- **THEN** the browser downloads one Markdown file containing distinct transcript and AI-advice sections without uploading the generated file to the server

#### Scenario: Review has no transcripts
- **WHEN** the owner downloads a review that only has question or AI-answer records
- **THEN** the file truthfully states that no persisted speech transcript is available and still includes the available review records

### Requirement: Review retention SHALL remain privacy bounded

The feature MUST NOT persist raw interview audio or create a server-side export attachment. Deleting the interview SHALL make its transcript review inaccessible under the same session deletion boundary.

#### Scenario: Owner deletes the interview
- **WHEN** the owner deletes the session
- **THEN** subsequent review API requests cannot retrieve its transcripts or generated review data
