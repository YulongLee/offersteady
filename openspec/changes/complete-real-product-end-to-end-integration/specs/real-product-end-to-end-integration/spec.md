## ADDED Requirements

### Requirement: Real product end-to-end integration SHALL execute the full OfferSteady business flow with real providers
The system SHALL provide a real end-to-end integration workflow that validates the complete OfferSteady business flow for login, Resume upload, JD upload, Knowledge upload, OSS storage, MinerU parsing, Embedding, pgvector storage, Retrieval, Interview Session, Chat, Screenshot, Speech, and History using configured real providers and infrastructure.

#### Scenario: Full real business flow execution
- **WHEN** an operator runs the real product end-to-end integration workflow in a prepared environment
- **THEN** the workflow SHALL execute the complete business path from login through history query
- **AND** each dependency in scope SHALL use the configured real provider or infrastructure instead of a placeholder adapter

### Requirement: Frontend integration mode SHALL not use mock or fixture data for core product state
The system SHALL provide a frontend integration mode in which core product state is loaded from real backend APIs and SHALL NOT use fixture, prototype, or mock state as the authoritative source for interviews, materials, billing balance, session state, or history.

#### Scenario: Frontend uses real API data
- **WHEN** the frontend is started in end-to-end integration mode
- **THEN** the interview list, materials list, billing state, active session state, and history state SHALL come from backend APIs
- **AND** the frontend SHALL fail the integration run if it falls back to fixture or mock state for those core product views

#### Scenario: Prototype interaction stays unchanged
- **WHEN** frontend integration mode is enabled
- **THEN** the approved page structure, route structure, and user interaction order SHALL remain unchanged
- **AND** no extra user-facing testing-only flow branches SHALL be introduced

### Requirement: Document pipeline SHALL use real storage, parsing, embedding, and vector persistence
The system SHALL validate that Resume, JD, and Knowledge documents complete a real pipeline through OSS storage, MinerU parsing, Markdown normalization, chunking, Embedding, and pgvector persistence before they are used in retrieval-backed product flows.

#### Scenario: Resume, JD, and Knowledge complete real processing
- **WHEN** a user uploads Resume, JD, and Knowledge documents during end-to-end integration
- **THEN** each document SHALL be stored in OSS, parsed through MinerU, embedded through the configured embedding provider, and persisted to pgvector-backed retrieval storage
- **AND** the resulting processing status SHALL be queryable through backend APIs

### Requirement: Retrieval, Chat, Screenshot, and Speech SHALL consume real processed context
The system SHALL validate that retrieval-backed product answers consume real processed context rather than synthetic or hard-coded provider outputs.

#### Scenario: Chat uses real retrieval context
- **WHEN** a user submits a question in an interview session with bound processed materials
- **THEN** the system SHALL retrieve relevant chunks from the configured retrieval path
- **AND** the chat answer SHALL be generated through the configured real LLM provider

#### Scenario: Screenshot answer uses real image understanding
- **WHEN** a user submits a screenshot answer request with one or more screenshots and an active interview session
- **THEN** the system SHALL call the configured real vision provider
- **AND** the resulting answer SHALL be based on real screenshot analysis plus retrieval context when available

#### Scenario: Speech flow uses real ASR-triggered session output
- **WHEN** realtime speech input is streamed into an active interview session during end-to-end integration
- **THEN** the system SHALL produce transcript events through the configured real ASR provider
- **AND** downstream answer generation SHALL stay bound to the same interview session and use the configured real AI stack

### Requirement: History SHALL reflect real persisted session artifacts
The system SHALL validate that conversation records, screenshots, transcripts, answers, and interview session history are queryable from the current backend system of record after a real integration run.

#### Scenario: Query history after session completion
- **WHEN** a real end-to-end session completes chat, screenshot, and speech interactions and then ends the interview session
- **THEN** the backend SHALL return history and conversation records for that session
- **AND** those records SHALL correspond to the real interactions executed during the integration run
