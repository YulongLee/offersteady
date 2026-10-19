## ADDED Requirements

### Requirement: Global written workspace has an optional English multi-screen mode
The Global written workspace SHALL show a keyboard-accessible English Multi-screen answers switch off on entry. Enabling it SHALL show separate Capture and Answer controls, ordered pending items and removal, with Answer disabled until a ready capture exists. Other modes and the off state MUST retain their current single-screen workflow.

#### Scenario: A Global user collects multiple pages
- **WHEN** a written user enables the switch and captures two views
- **THEN** the English UI shows two ordered items and allows one explicit Answer submission

#### Scenario: Other modes or switch off
- **WHEN** the mode is not written or the switch is off
- **THEN** current single capture-and-answer and all existing controls remain available

### Requirement: Collection and batch answering preserve Global usage rules
Capture-only SHALL default to false and, when explicitly requested for an active written session, MUST NOT invoke a model or reserve/settle usage. Answer SHALL submit at most four valid owned ordered captures as one streamed task with exactly one existing Global screenshot usage operation. It MUST NOT access domestic points or alter Global paid/free entitlement rules.

#### Scenario: Paid and free entitlement behavior
- **WHEN** a paid or free Global user submits a valid batch
- **THEN** the existing Global reservation/settlement rules authorize or reject one screenshot task, with no domestic ledger or additional per-image charge

#### Scenario: Capture before answering
- **WHEN** a user only collects screenshots or removes pending items
- **THEN** no answer history, provider request or billable usage is created

### Requirement: Batch ownership idempotency and cleanup remain bounded
The server MUST enforce same owner, active written session, nonduplicate ordered sources, available unconsumed images and count limits. Repeated acceptance of the same batch MUST return the same work without duplicate generation or usage. Cancel/remove/leave/end/expiry MUST clean unused bytes and reject late callbacks without reviving or charging cancelled work. Images MUST NOT enter browser persistence or diagnostic logs, and no Resume/JD/Knowledge context SHALL be added.

#### Scenario: Duplicate forged or expired input
- **WHEN** a batch is repeated or includes another owner, invalid scope, duplicate, expired or consumed sources
- **THEN** a valid repeat returns its existing request while invalid input invokes no model or billing

#### Scenario: Cancellation overlaps capture or answer
- **WHEN** cancellation overlaps an upload, callback or generation
- **THEN** terminal state remains cancelled, no late answer is published, and unused bytes are released
