## ADDED Requirements

### Requirement: Session-scoped web answer toggle

The domestic live interview client SHALL expose a session-scoped web-answer toggle that defaults to disabled and is sent as `webSearchEnabled` with each answer request.

#### Scenario: Existing request without the flag
- **WHEN** an old client omits `webSearchEnabled`
- **THEN** the server SHALL run the existing local retrieval answer flow without a web search

#### Scenario: User enables web answer
- **WHEN** the user enables the web-answer control for a live session
- **THEN** subsequent manual and auto answer requests for that session SHALL carry `webSearchEnabled=true` until disabled or the session ends

### Requirement: Detailed-stage-only web retrieval

When web answer is enabled and the request is eligible, the service SHALL keep the quick stage on the existing low-latency path and SHALL invoke web retrieval only before the detailed stage.

#### Scenario: Quick answer remains available first
- **WHEN** a web-enabled streaming answer starts
- **THEN** the SSE stream SHALL emit quick-answer chunks before any web-search status or detailed-answer chunks

#### Scenario: Web search succeeds
- **WHEN** the search gateway returns valid sources within the configured timeout
- **THEN** the detailed prompt SHALL contain a bounded web-source section and the completed task SHALL expose the source metadata

### Requirement: Source-grounded response

The detailed prompt SHALL require the model to distinguish web-source facts from user materials and model suggestions, and the API SHALL return source title, URL, short snippet, and retrieval timestamp without storing full web pages.

#### Scenario: Sources are shown
- **WHEN** a web-grounded detailed answer completes
- **THEN** the task response SHALL include a `webSources` list and the client SHALL provide a collapsible sources presentation

### Requirement: Safe fallback

Web-search failure, timeout, empty results, or an unavailable provider SHALL fall back to the existing local retrieval detailed answer and SHALL not fail a request that can be completed locally.

#### Scenario: Search provider timeout
- **WHEN** web retrieval exceeds its timeout
- **THEN** the service SHALL mark web search as unavailable, continue with local context, and return a user-visible non-blocking fallback status

### Requirement: Minimal third-party context

The service SHALL send only the normalized interview question and bounded non-sensitive context to the search provider, and SHALL NOT send raw audio, screenshots, full resumes, or complete conversation history by default.

#### Scenario: Sensitive material is present
- **WHEN** the session contains a resume, screenshot, or audio transcript
- **THEN** the web query SHALL exclude those raw artifacts unless a future explicit consent flow is enabled

### Requirement: Search observability

The service SHALL record web-search duration, source count, provider status, fallback reason, and billing source without logging query text or page content.

#### Scenario: Search telemetry is emitted
- **WHEN** a web search attempt finishes or falls back
- **THEN** a structured event SHALL include safe status fields and SHALL omit the question and source snippets
