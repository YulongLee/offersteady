## ADDED Requirements

### Requirement: Clear control and status

The live interview answer controls SHALL show a labeled web-answer control next to the automatic-answer control, with a disabled, enabled, checking, unavailable, and fallback state that does not obscure existing answers.

#### Scenario: Default presentation
- **WHEN** the user opens a live interview
- **THEN** the web-answer control SHALL be visible, off by default, and explain that detailed answers may use current web sources

#### Scenario: Search in progress
- **WHEN** a web-enabled answer is in the detailed stage
- **THEN** the client SHALL show a non-blocking “正在联网查找” status while preserving the already visible quick answer

### Requirement: Independent answer-stage presentation

The client SHALL render simple-answer chunks as they arrive and mark the simple section completed when the server signals quick-stage completion, without waiting for web search or detailed generation. The detailed section SHALL show its own waiting, generating, fallback, or failure state. Whole-task cancellation and duplicate-submission protection SHALL remain active until the whole task terminates.

#### Scenario: Search remains pending after simple answer completes
- **WHEN** quick-stage completion arrives while the web provider has not returned
- **THEN** desktop and mobile SHALL immediately format the simple answer as completed and show detailed generation separately without declaring the whole task complete

#### Scenario: Detail fails or falls back
- **WHEN** detail processing fails or web search falls back after quick completion
- **THEN** the completed simple text SHALL remain readable and SHALL NOT resume its loading state

#### Scenario: Older server and stale task updates
- **WHEN** an older response omits quick-stage metadata
- **THEN** the client SHALL preserve its existing behavior and MAY recognize the existing detailed-section boundary as completion of the simple section
- **AND** a delayed completion from a cancelled or superseded task SHALL NOT overwrite the current answer

### Requirement: Language-aware web answer

The web query, source labels, and detailed answer SHALL follow the selected interview language while preserving source URLs and provider metadata.

#### Scenario: English interview
- **WHEN** the session language is English and web answer is enabled
- **THEN** the search query and detailed answer instructions SHALL request English output and the UI SHALL label sources in English

### Requirement: Feature remains opt-in

The client SHALL not enable web search merely because a user has a membership or points balance.

#### Scenario: Member enters interview
- **WHEN** a seven-day member enters a new interview without touching the control
- **THEN** web search SHALL remain disabled and no web provider request SHALL be made

### Requirement: Turning web mode off restores ordinary answers

The client SHALL cancel an in-flight web answer when web mode is disabled, preserve already visible answer text, and immediately allow an ordinary quick-answer request. Turning the switch on or off SHALL NOT cancel an ordinary answer or a screenshot answer.

#### Scenario: Turn off while searching
- **WHEN** a web answer is waiting for search and the user disables web mode
- **THEN** the client SHALL request cancellation, detach the old stream, and unlock quick answer without waiting for the search timeout
- **AND** late stream events, realtime task updates, and cleanup from the old request SHALL NOT replace or unlock a newer request

#### Scenario: Turn off before task acknowledgement
- **WHEN** web mode is disabled before the server task ID is received
- **THEN** the client SHALL abort the request and restore ordinary quick answer, and the server SHALL clean up any started task when it observes the disconnect

#### Scenario: Repeat the same question in another mode
- **WHEN** a user submits the same question after switching web mode, whether the previous answer completed, failed, or was cancelled
- **THEN** the new intentional request SHALL have a distinct mode-aware request ID without question text, while duplicate clicks during one in-flight request SHALL remain suppressed
