## ADDED Requirements

### Requirement: The system MUST provide one authoritative interview session service
The system SHALL provide one authoritative Interview Session Service that owns the lifecycle, context scope, and configuration scope of a single AI interview session for downstream services.

#### Scenario: Session is created for a new interview
- **WHEN** an authorized client creates a new interview session
- **THEN** the system MUST return one session identifier and initialize a server-owned session record instead of scattering state across independent feature modules

#### Scenario: Downstream services consume session context
- **WHEN** Retrieval, Answer, Screenshot, or Desktop Bridge services need interview context
- **THEN** they MUST consume the session identifier and session-owned context boundaries rather than maintaining their own primary interview state

### Requirement: The interview session service MUST manage the session lifecycle
The system SHALL manage interview sessions through explicit lifecycle states so the product can support preparation, continuation, live interviewing, ending, and historical recovery without changing the approved prototype flow.

#### Scenario: Session starts in preparation
- **WHEN** a user creates a new interview session
- **THEN** the session MUST begin in a preparation-oriented state that supports material selection and configuration before the interview starts

#### Scenario: Session enters live interview
- **WHEN** the user starts the interview from the preparation flow
- **THEN** the system MUST transition the session to a live state and preserve the confirmed session context

#### Scenario: Session is ended
- **WHEN** the user explicitly ends the interview
- **THEN** the system MUST mark the session as ended and prevent it from being treated as an active live session

### Requirement: One session MUST support multiple bound documents across Resume, JD, and Knowledge Base
The system SHALL allow a single interview session to bind zero or more approved documents from Resume, JD, and Knowledge Base, while preserving session-level selection snapshots and material scope for downstream retrieval and answer services.

#### Scenario: Session binds one resume, one JD, and multiple knowledge documents
- **WHEN** the user confirms the session materials during preparation
- **THEN** the system MUST persist the selected Resume, JD, and zero or more Knowledge Base document identifiers as session-bound context

#### Scenario: Session confirms an empty material set
- **WHEN** the user explicitly confirms that no Resume, JD, or Knowledge Base documents will be used
- **THEN** the system MUST persist an empty session material scope rather than auto-inheriting account-level documents

#### Scenario: Bound materials become unavailable later
- **WHEN** a document previously selected for the session is deleted, revoked, or no longer ready
- **THEN** the session service MUST preserve the historical binding record and expose that the bound source is no longer active, rather than silently replacing it

### Requirement: The session service MUST snapshot model, prompt, and retrieval configuration
The system SHALL persist a session-scoped configuration snapshot that records the active model configuration, prompt configuration, and retrieval configuration for the interview session.

#### Scenario: Session is prepared with active runtime configuration
- **WHEN** a user confirms the interview session before starting
- **THEN** the system MUST store the model, prompt, and retrieval configuration snapshot that applies to that session

#### Scenario: Downstream service reads session configuration
- **WHEN** a downstream AI service is invoked for a session
- **THEN** the system MUST provide the session-owned configuration snapshot instead of requiring that service to infer configuration from mutable global defaults

### Requirement: The session service MUST manage multi-turn conversation context
The system SHALL manage structured conversation context for each interview session so later AI services can consume multi-turn history without owning the conversation state themselves.

#### Scenario: Session receives multiple turns
- **WHEN** the interview session accumulates interviewer utterances, candidate utterances, manual questions, screenshot tasks, or AI advice records
- **THEN** the system MUST append them as ordered session context records that preserve role, source, timestamps, and visibility boundaries

#### Scenario: Session is restored after interruption
- **WHEN** the user resumes a recoverable interview session
- **THEN** the system MUST return enough ordered conversation context to reconstruct the current interview state without requiring the client to rebuild it from unrelated services

### Requirement: The session service MUST track session-level token usage
The system SHALL track token usage statistics at the interview session level so future billing, quota, and analytics services can attribute model usage to the correct interview.

#### Scenario: Session consumes AI tokens
- **WHEN** an AI-related task records prompt tokens, completion tokens, or total tokens for a session
- **THEN** the system MUST update session-level usage totals and preserve structured usage records for that session

#### Scenario: Session usage is queried
- **WHEN** an authorized client or downstream service requests usage data for a session
- **THEN** the system MUST return session-scoped usage totals instead of only provider-local raw counters

### Requirement: The session service MUST support historical recovery and explicit continuation
The system SHALL support listing and restoring historical interview sessions so the approved “继续面试” product flow can resolve to the correct preparation or live state.

#### Scenario: Preparing session is continued
- **WHEN** the client requests a still-preparing interview session
- **THEN** the system MUST return the saved material selection, configuration snapshot, and other recoverable preparation context for that session

#### Scenario: Live session is continued
- **WHEN** the client requests an in-progress or recoverable live session
- **THEN** the system MUST return the latest authoritative session state and session context needed to reopen the live workspace directly

### Requirement: The session service MUST support ending and restarting an interview
The system SHALL support ending a session and restarting from a previous interview context without mutating completed historical records into a different interview.

#### Scenario: End interview keeps history but closes activity
- **WHEN** the user ends an interview session
- **THEN** the system MUST preserve the historical session record while marking it unavailable for further active interview commands

#### Scenario: Restart interview from previous context
- **WHEN** the user chooses to restart from a prior interview
- **THEN** the system MUST create a new session seeded from the prior session’s reusable configuration and approved material scope instead of rewriting the previous session in place

### Requirement: The session service MUST remain decoupled from chat generation and streaming transport
The system SHALL manage interview context and state without directly embedding Chat Service behavior, streaming transport details, or provider-specific LLM invocation into the session lifecycle contract.

#### Scenario: Session service is used before chat exists
- **WHEN** the system creates, restores, or ends a session before Chat Service is implemented
- **THEN** the session lifecycle and context APIs MUST remain valid without requiring LLM execution

#### Scenario: Session service is used with multiple downstream adapters
- **WHEN** downstream services evolve or provider adapters change
- **THEN** the session contract MUST remain stable enough that chat, retrieval, screenshot, or desktop transport integrations can change independently
