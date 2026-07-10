## ADDED Requirements

### Requirement: End-to-end integration SHALL execute the full OfferSteady product flow with real dependencies
The system SHALL provide an end-to-end integration workflow that validates the full OfferSteady product flow using real APIs, real infrastructure, and real backend orchestration for registration, authentication, file upload, document processing, retrieval, interview session, chat, screenshot answer, realtime speech, conversation storage, and interview history.

#### Scenario: Full product flow integration
- **WHEN** an operator runs the end-to-end integration workflow in a prepared environment
- **THEN** the system executes the full product flow from user registration or login through final interview history retrieval
- **AND** every external dependency in scope SHALL use the configured real provider or infrastructure service

### Requirement: Frontend integration mode SHALL use real API data without changing approved prototype interactions
The system SHALL provide a frontend integration mode that uses real backend APIs while preserving the approved prototype page structure, user flow, and interaction order.

#### Scenario: Frontend uses API mode
- **WHEN** a frontend integration run starts
- **THEN** the frontend SHALL use the real API data source instead of mock or fixture output
- **AND** the approved prototype routes, structure, and interaction order SHALL remain unchanged

#### Scenario: Prototype integrity during integration
- **WHEN** end-to-end integration is enabled
- **THEN** no additional product pages, user-visible flow branches, or reordered interactions are introduced solely for testing

### Requirement: Document ingestion path SHALL complete through OSS, parser, chunking, embedding, and pgvector
The system SHALL validate that Resume, JD, and Knowledge Base uploads pass through OSS storage, document processing, parser, Markdown normalization, chunking, embedding, and pgvector storage before they are eligible for retrieval or interview use.

#### Scenario: Resume pipeline completion
- **WHEN** a user uploads a Resume during end-to-end integration
- **THEN** the system SHALL store the file in OSS, complete document processing, and make the processed document available for retrieval-backed interview assistance

#### Scenario: JD and Knowledge pipeline completion
- **WHEN** a user uploads a JD and a Knowledge Base file during end-to-end integration
- **THEN** the system SHALL complete the same processing pipeline and expose both documents to retrieval filters for the active interview session

### Requirement: Retrieval and answer generation SHALL use real processed context
The system SHALL validate that Retrieval, Chat Service, Screenshot Answer, and Realtime Speech consume real processed materials and produce session-bound outputs.

#### Scenario: Chat answer uses uploaded context
- **WHEN** a live interview question is submitted in an interview session with bound Resume, JD, or Knowledge materials
- **THEN** the system SHALL retrieve relevant context from processed documents and return a real AI-generated answer through the configured provider

#### Scenario: Screenshot answer uses vision and retrieval
- **WHEN** a screenshot answer request is submitted with a screenshot and an active interview session
- **THEN** the system SHALL call the real vision provider, combine it with retrieval context when available, and return a real answer result

#### Scenario: Realtime speech triggers transcript and answer flow
- **WHEN** realtime speech input is streamed into an active interview session
- **THEN** the system SHALL produce transcript events using the real realtime ASR provider
- **AND** the downstream answer flow SHALL remain session-bound and query the configured AI stack

### Requirement: Conversation and history SHALL be queryable after end-to-end execution
The system SHALL preserve conversation artifacts and interview history in the current system of record so they can be queried after end-to-end execution.

#### Scenario: Conversation storage retrieval
- **WHEN** an end-to-end scenario completes a chat, screenshot answer, or realtime speech interaction
- **THEN** the resulting conversation records SHALL be retrievable from the service-side conversation storage boundary

#### Scenario: Interview history retrieval
- **WHEN** an end-to-end scenario ends an interview session
- **THEN** the system SHALL expose the resulting interview history through the configured history query path

### Requirement: End-to-end integration SHALL output an integration report with provider and scenario status
The system SHALL output an Integration Report that distinguishes provider readiness, scenario readiness, and failure attribution.

#### Scenario: Integration report generation
- **WHEN** an end-to-end integration run completes
- **THEN** the system SHALL generate an Integration Report containing executed scenarios, provider results, final status, and failure attribution

#### Scenario: Failure attribution
- **WHEN** an end-to-end scenario fails
- **THEN** the report SHALL identify whether the failure originated from frontend API mode, backend orchestration, test fixture preparation, or third-party provider / infrastructure
