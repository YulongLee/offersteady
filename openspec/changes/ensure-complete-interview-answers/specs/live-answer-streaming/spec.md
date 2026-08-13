## MODIFIED Requirements

### Requirement: Live answer generation MUST support incremental answer events

The system MUST provide a live-answer streaming path that emits ordered answer events while the model is generating. Automatic continuation MUST remain within the same answer task, MUST preserve previously emitted text, and MUST continue monotonically increasing chunk sequence numbers. A completed event MUST NOT be emitted while either the quick or detailed stage is incomplete.

#### Scenario: Automatic continuation appends text
- **WHEN** a quick or detailed stage requires continuation
- **THEN** the backend emits only the missing suffix as additional ordered chunks under the existing task

#### Scenario: Stream completes after continuation
- **WHEN** both stages reach a complete terminal result after one or more continuations
- **THEN** the backend emits one completed event whose persisted final text matches the complete visible text

#### Scenario: Stream cannot complete safely
- **WHEN** bounded continuation attempts are exhausted
- **THEN** the backend emits a failed event with preserved partial text and does not emit completed
