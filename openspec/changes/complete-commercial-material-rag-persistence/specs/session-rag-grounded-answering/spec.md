## ADDED Requirements

### Requirement: Interview RAG uses only confirmed session material versions
The system SHALL retrieve answer context only from material versions explicitly confirmed for the current interview session revision and MUST NOT search the user's entire material library by default.

#### Scenario: User asks a live interview question
- **WHEN** a live answer is requested for an interview with confirmed Resume, JD or Knowledge material versions
- **THEN** the retrieval service searches only those confirmed versions and returns structured context for answer generation

#### Scenario: User has unselected ready materials
- **WHEN** the user's library contains ready materials that were not confirmed for the session
- **THEN** those materials are excluded from retrieval and answer grounding for that session

### Requirement: Retrieval respects document status and deletion
The system SHALL exclude deleted, disabled, failed, processing or non-indexed material versions from RAG retrieval even if a stale session selection references them.

#### Scenario: Confirmed source is deleted after selection
- **WHEN** a confirmed material version is deleted before a future question is answered
- **THEN** the retrieval service excludes its chunks and reports a deleted source marker rather than silently substituting another material

### Requirement: Generated answers expose safe provenance
The system SHALL include safe provenance in generated answer records and UI payloads, including source display name, kind, version, deleted marker when applicable and short evidence summary, without exposing raw full documents or internal prompts.

#### Scenario: Answer uses retrieved knowledge
- **WHEN** an answer is generated with retrieved Resume, JD or Knowledge context
- **THEN** the answer provenance lists the source labels and versions used to ground the suggestion

#### Scenario: No relevant context is found
- **WHEN** retrieval returns no relevant chunk for the confirmed materials
- **THEN** the answer states that no matching personal material was used and MUST NOT fabricate candidate company, project, responsibility or metric details

### Requirement: Screenshot answers share the same session RAG boundary
The system SHALL use the same confirmed session material snapshot and retrieval filters when generating screenshot-based answers.

#### Scenario: Screenshot answer is requested
- **WHEN** a screenshot answer request is submitted in an interview session with confirmed materials
- **THEN** the system combines vision summary with retrieval context from only the confirmed material versions

### Requirement: RAG operations avoid sensitive ordinary logs
The system SHALL log retrieval status, source IDs, counts, latency and safe error codes while excluding full questions, raw document text, screenshots, full prompts, embeddings and provider payloads from ordinary logs.

#### Scenario: Retrieval completes
- **WHEN** a retrieval request completes for a live answer
- **THEN** ordinary logs contain operational metadata but not raw material content or model prompt content
