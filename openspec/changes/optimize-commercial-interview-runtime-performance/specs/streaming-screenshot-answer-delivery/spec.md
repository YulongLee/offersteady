## ADDED Requirements

### Requirement: Screenshot answers expose incremental text
The system SHALL expose monotonic screenshot answer text before the vision provider finishes when the configured provider supports streaming, while preserving the same final answer content policy and screenshot-only evidence boundary.

#### Scenario: First screenshot text arrives before completion
- **WHEN** a user explicitly starts a screenshot answer and the provider emits partial text
- **THEN** the current answer workspace displays the accumulated text before the task reaches completed state

#### Scenario: Provider lacks streaming support
- **WHEN** the configured vision provider does not support a valid streaming response
- **THEN** the system falls back to the existing complete-response path without duplicating billing or creating a second task

### Requirement: Screenshot progress is monotonic and recoverable
The system MUST publish throttled screenshot task revisions through the ordered session event stream and MUST prevent older progress, retries, or snapshots from shortening visible text or replacing a terminal task.

#### Scenario: Duplicate or delayed progress arrives
- **WHEN** the browser receives repeated or out-of-order screenshot task updates
- **THEN** it retains the newest terminal state and the longest valid monotonic answer prefix

#### Scenario: User cancels during streaming
- **WHEN** the user cancels a screenshot answer before completion
- **THEN** generation stops when supported, reserved billing is released according to existing rules, and later partial events do not revive the task
