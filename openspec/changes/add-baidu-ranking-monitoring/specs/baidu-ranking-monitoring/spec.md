## ADDED Requirements

### Requirement: Server-side ranking configuration

The system SHALL read the ranking provider endpoint, server-side credentials, target domain, and keyword list from protected configuration and SHALL never expose credentials to browser responses, frontend bundles, logs, or audit details.

#### Scenario: Missing or invalid provider configuration
- **WHEN** the ranking task starts without a complete endpoint/credential/domain configuration
- **THEN** the task records `invalid_config`, does not call the provider, and leaves normal user requests unaffected

#### Scenario: Credential secrecy
- **WHEN** an administrator reads ranking status or the frontend loads the ranking view
- **THEN** the response contains configuration status and safe fingerprints only, never the credential values

### Requirement: Daily idempotent synchronization

The system SHALL synchronize each configured domain-keyword pair at most once per Asia/Shanghai calendar day, with bounded timeout/retry behavior and an idempotent persistence key.

#### Scenario: First daily synchronization
- **WHEN** the scheduled task runs for a configured keyword with no snapshot for today
- **THEN** it queries the provider, persists one result for that domain-keyword-date, and records the provider status and observed timestamp

#### Scenario: Duplicate task execution
- **WHEN** two workers run the same daily task concurrently or the task is retried after success
- **THEN** only one snapshot remains for the domain-keyword-date and no duplicate result is shown

#### Scenario: Provider timeout or rate limit
- **WHEN** a provider request exceeds the configured timeout or returns a retryable error
- **THEN** the task performs only the configured bounded retries, records a safe failure status, and does not block user-facing API traffic

### Requirement: Rank status semantics

The system SHALL distinguish a ranked result, a successful query with no result in the provider return range, and provider/configuration failures.

#### Scenario: Keyword is ranked
- **WHEN** the provider returns a rank from 1 through 50 with a matching URL or title
- **THEN** the snapshot status is `ranked` and stores the integer rank plus the returned URL/title

#### Scenario: Keyword is outside return range
- **WHEN** the provider succeeds but does not return the keyword within its documented result range
- **THEN** the snapshot status is `not_found` and the UI displays that it was not found in the returned range, not rank 0

### Requirement: Protected admin ranking view and keyword management

The system SHALL provide a permission-protected admin endpoint and view that show configured keywords, the latest snapshot, previous-rank delta, observed date, provider status, and up to 50 returned results (rank, URL, and title) for each keyword without triggering a provider call during page load. Authorized managers SHALL be able to add, deactivate, and edit keywords without changing historical snapshots.

#### Scenario: Authorized administrator views rankings
- **WHEN** an administrator with the ranking read permission opens the Search Rankings view
- **THEN** the backend returns the latest stored snapshots and last sync summary, and the UI renders up to 50 results per keyword in a table

#### Scenario: Authorized manager edits keywords
- **WHEN** an administrator with the ranking management permission adds or deactivates a keyword
- **THEN** the new configuration is validated, the change is audited, and existing historical snapshots remain unchanged

#### Scenario: Unauthorized administrator requests rankings
- **WHEN** a session without the ranking read permission requests the endpoint
- **THEN** the backend returns a permission error and records the denied permission check using the existing audit mechanism

### Requirement: Audited manual refresh

The system SHALL provide a permission-protected, rate-limited, audited manual refresh action for configured keywords.

#### Scenario: Audited manual refresh
- **WHEN** an authorized administrator requests a permitted refresh with a reason
- **THEN** the backend runs the bounded synchronization, returns the resulting status, and writes an audit record without storing credentials
