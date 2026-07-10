## ADDED Requirements

### Requirement: Material access is owner-scoped across DB and OSS
The system SHALL enforce owner_user_id boundaries for material records, artifact records, upload intents, deletion jobs and generated OSS object keys. Clients MUST NOT be able to select or read another user's material by providing IDs or object keys.

#### Scenario: User selects another user's document ID
- **WHEN** a user attempts to confirm a document owned by another user for an interview
- **THEN** the backend rejects the request and does not reveal sensitive document details

#### Scenario: Client submits arbitrary object key
- **WHEN** a client provides an object key not created by the backend for that user and upload intent
- **THEN** upload completion or artifact access is rejected

### Requirement: RAG retrieval is restricted to confirmed session materials
The system SHALL restrict RAG retrieval to the current user's confirmed session material snapshot and MUST NOT search unconfirmed library materials or another user's vector chunks.

#### Scenario: Session has confirmed knowledge materials
- **WHEN** an answer request runs retrieval
- **THEN** the retrieval filter includes only confirmed Knowledge document version IDs for that session and owner

#### Scenario: User has other library materials
- **WHEN** a user owns additional Knowledge materials that were not confirmed for the session
- **THEN** those materials are excluded from retrieval for the current answer

### Requirement: Sensitive content is excluded from logs and traces
The system SHALL keep logs, usage records and RAG traces free of raw sensitive content, including resume text, JD text, screenshots, full prompts, embeddings and provider payloads.

#### Scenario: Provider call fails
- **WHEN** an AI provider returns an error
- **THEN** the backend logs a safe error code, provider name, model name and trace ID without storing raw request or response payloads
