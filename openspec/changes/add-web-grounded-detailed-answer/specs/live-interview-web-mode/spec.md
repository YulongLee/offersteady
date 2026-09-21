## ADDED Requirements

### Requirement: Clear control and status

The live interview answer controls SHALL show a labeled web-answer control next to the automatic-answer control, with a disabled, enabled, checking, unavailable, and fallback state that does not obscure existing answers.

#### Scenario: Default presentation
- **WHEN** the user opens a live interview
- **THEN** the web-answer control SHALL be visible, off by default, and explain that detailed answers may use current web sources

#### Scenario: Search in progress
- **WHEN** a web-enabled answer is in the detailed stage
- **THEN** the client SHALL show a non-blocking “正在联网查找” status while preserving the already visible quick answer

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
