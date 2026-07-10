## ADDED Requirements

### Requirement: Third-party verification suite SHALL execute real integrations
The system SHALL provide a repeatable verification suite that executes real third-party integrations for OSS upload/download, MinerU parsing, Qwen chat, Qwen vision, embedding, rerank, realtime ASR, PostgreSQL, and pgvector without changing approved product prototype behavior.

#### Scenario: Full verification run
- **WHEN** an operator runs the full verification suite in an environment with all required credentials and endpoints configured
- **THEN** the system executes every integration item against the real external service or infrastructure connection
- **AND** the system returns a per-item status, execution duration, and final suite summary

#### Scenario: Verification does not alter prototype behavior
- **WHEN** the verification suite is added to the system
- **THEN** the approved web prototype routes, page structure, and product interactions remain unchanged

### Requirement: Verification suite SHALL use real providers with safe test fixtures
The system SHALL require real API calls and real infrastructure connections for integration verification, while restricting test inputs to synthetic or sanitized fixtures.

#### Scenario: Real provider execution
- **WHEN** an operator executes a provider verification
- **THEN** the system sends the request to the configured real provider endpoint using server-side credentials
- **AND** the system MUST NOT replace the call with an in-memory stub, fixture response, or mock adapter

#### Scenario: Safe fixture usage
- **WHEN** a verification requires a document, image, audio sample, or prompt input
- **THEN** the system uses synthetic or sanitized test fixtures
- **AND** the system MUST NOT require real user resume, JD, screenshot, audio, or knowledge data

### Requirement: Verification suite SHALL produce structured logs and integration reports
The system SHALL produce structured execution logs and a repeatable Integration Report for every verification run.

#### Scenario: Report generation
- **WHEN** a verification run completes successfully or with failures
- **THEN** the system generates an Integration Report containing environment label, executed items, per-item result, key metrics, and overall conclusion

#### Scenario: Log generation
- **WHEN** a verification step starts, succeeds, retries, or fails
- **THEN** the system records a structured log entry with the provider, step name, status, timing, and sanitized error details

### Requirement: Verification suite SHALL support status granularity and reruns
The system SHALL track item-level and step-level verification states and support repeatable re-execution for failed or targeted checks.

#### Scenario: Targeted rerun
- **WHEN** an operator chooses to rerun only one integration item after a failure
- **THEN** the system executes only the selected verification item
- **AND** the report clearly distinguishes the rerun from previous runs

#### Scenario: Step-level failure visibility
- **WHEN** a multi-step verification item fails
- **THEN** the system identifies the failed step and preserves the statuses of completed prior steps in the report

### Requirement: Verification suite SHALL protect credentials and sensitive content
The system SHALL keep third-party credentials on the trusted server side and SHALL sanitize report and log output so that secrets and raw sensitive materials are not exposed.

#### Scenario: Server-side credential handling
- **WHEN** the verification suite calls a third-party service
- **THEN** the system reads credentials from server-side configuration only
- **AND** the system MUST NOT expose secret values to client-side code or report payloads

#### Scenario: Sanitized outputs
- **WHEN** the system writes logs or reports for a verification run
- **THEN** the system redacts or summarizes credentials, raw document bodies, raw screenshot content, and long audio transcripts

