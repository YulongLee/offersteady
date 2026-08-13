## ADDED Requirements

### Requirement: Every answer stage MUST have a complete terminal result

The system MUST evaluate the quick and detailed stages independently and MUST mark the answer task completed only after both stages terminate normally with non-empty, complete text.

#### Scenario: Both stages finish normally
- **WHEN** the quick and detailed model streams return complete text with a normal terminal reason
- **THEN** the backend persists one completed task containing both complete stages

#### Scenario: A stage is length-truncated
- **WHEN** either stage reports a length terminal reason
- **THEN** the backend does not mark the task completed and continues only that stage

### Requirement: Incomplete stages MUST be continued without losing visible text

The system MUST preserve already emitted text, request only the missing suffix, remove repeated overlap, and emit new suffix chunks under the same task with monotonically increasing sequence numbers.

#### Scenario: Detailed answer reaches its output limit
- **WHEN** the detailed stage ends because of its output limit after the user has seen partial text
- **THEN** the system keeps the partial text visible and appends the continuation without clearing or shortening it

#### Scenario: Provider repeats the prior ending
- **WHEN** a continuation begins with text already present at the end of the existing stage
- **THEN** the repeated overlap appears only once in the final answer

### Requirement: Incomplete answer retries MUST be bounded and truthful

The system MUST apply a server-side continuation attempt limit. If a stage remains incomplete after the limit, the task MUST retain partial text and transition to failed with a safe error code instead of completed.

#### Scenario: Continuation attempts are exhausted
- **WHEN** all permitted continuation attempts still terminate by length or with obviously incomplete syntax
- **THEN** the stream emits a failed terminal event with partial text and `chat_answer_incomplete`

### Requirement: Completion diagnostics MUST protect interview content

The system MAY log stage, normalized terminal reason, continuation count, model, duration and size bucket, but MUST NOT log the question, answer, Prompt, raw provider body, transcript, resume, JD, or knowledge text.

#### Scenario: A continuation occurs
- **WHEN** a stage requires automatic continuation
- **THEN** diagnostics record safe structural metadata only
