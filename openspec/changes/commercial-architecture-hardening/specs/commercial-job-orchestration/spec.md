## ADDED Requirements

### Requirement: Long-running material work runs through durable jobs
The system SHALL represent material parsing, normalization, chunking, embedding, indexing, deletion cleanup and reconciliation as durable backend jobs rather than relying on a single foreground API request to complete them.

#### Scenario: Upload completion creates a processing job
- **WHEN** a user completes a material upload
- **THEN** the API records a processing job and returns a material processing state without waiting for MinerU, embedding or vector indexing to finish

#### Scenario: Worker resumes queued work
- **WHEN** the worker starts and queued processing jobs exist
- **THEN** it can claim jobs, update their running state and continue processing without requiring the original browser request

### Requirement: Jobs expose safe lifecycle and retry state
The system SHALL persist job stage, status, retry count, max retries, safe error code and timestamps. Job failures MUST be retryable when the failure is transient and MUST NOT expose provider payloads or sensitive document content.

#### Scenario: Provider timeout occurs
- **WHEN** MinerU, embedding, rerank, vision or chat provider times out during a job
- **THEN** the job records a safe retryable error code and increments retry count without storing provider raw payload

#### Scenario: Job exceeds max retries
- **WHEN** a job reaches its maximum retry count
- **THEN** the related material or cleanup state becomes failed with a safe user-facing reason

### Requirement: API paths remain responsive
The system SHALL keep interview creation, material confirmation and material status queries free from long-running processing, deletion or reconciliation work.

#### Scenario: User confirms interview materials
- **WHEN** selected materials are already selectable in the database
- **THEN** material confirmation performs lightweight database validation and does not run MinerU, embedding, vector indexing or broad OSS scans
