## ADDED Requirements

### Requirement: Source turns have a bounded monotonic lifecycle
The system SHALL manage microphone and system-output utterances as independent source-scoped turns with stable segment identity and monotonically increasing revisions. A turn that reaches `final` or `incomplete` MUST NOT return to an active transcribing state.

#### Scenario: Confirmed turn receives a delayed partial
- **WHEN** a delayed or replayed partial revision arrives after the same segment became final
- **THEN** the system ignores the partial lifecycle regression and keeps the turn confirmed

#### Scenario: New speech follows a confirmed turn
- **WHEN** the same role starts speaking after its previous turn became terminal
- **THEN** the system creates a new segment identity and leaves the previous turn immutable

### Requirement: Endpointing tolerates real meeting audio
The companion MUST determine source-specific turn boundaries using bounded adaptive noise evidence, start/continue hysteresis, buffered speech tails, and a maximum turn deadline. Persistent low-level system-output noise MUST NOT keep one turn active indefinitely.

#### Scenario: Interviewer stops while system-output noise continues
- **WHEN** meaningful system-output speech ends but a stable low-level background signal remains
- **THEN** the companion finalizes the interviewer turn within the configured bounded endpoint window without waiting for the maximum turn duration

#### Scenario: Candidate pauses naturally inside one sentence
- **WHEN** microphone speech contains a pause shorter than the configured candidate speech tail
- **THEN** the companion preserves one segment identity and continues the same turn without clipping the following words

#### Scenario: Continuous signal reaches the hard boundary
- **WHEN** speech or noise prevents a normal endpoint until the maximum turn deadline
- **THEN** the companion emits exactly one terminal frame for the bounded segment and starts later speech as a new segment

### Requirement: Terminal audio work cannot be silently lost
The desktop and backend MUST prioritize, idempotently identify, and acknowledge terminal frames independently of coalescible interim revisions. Queue pressure MAY coalesce obsolete partial revisions but MUST NOT silently discard the latest audio required to terminate a segment.

#### Scenario: Ingress queue is full when final arrives
- **WHEN** a terminal frame arrives while the source queue is at capacity
- **THEN** the system replaces or coalesces obsolete partial work to admit the terminal frame and returns an explicit terminal acknowledgement or explicit degraded failure

#### Scenario: Connection drops before acknowledgement
- **WHEN** the companion sends a terminal frame and disconnects before receiving its acknowledgement
- **THEN** it resends the same segment ID and terminal revision after reconnect and the backend processes the terminal intent at most once

### Requirement: Stalled turns recover without blocking the interview
The backend MUST supervise each active source and move a stalled turn to `final` only after authoritative provider completion, otherwise to `incomplete`, within a bounded watchdog interval. Recovery MUST recreate only the affected source session and MUST reject late events from its retired generation.

#### Scenario: Desktop final never arrives
- **WHEN** a source has an active segment and no newer audio or terminal frame arrives before the watchdog boundary
- **THEN** the backend attempts a bounded provider commit and publishes one terminal result or one incomplete recovery state

#### Scenario: Provider completion is missing
- **WHEN** the provider does not return a completion before the finalization timeout
- **THEN** the system marks the turn incomplete, recreates only that source connection, and continues accepting later speech

#### Scenario: Other channel remains healthy
- **WHEN** system-output ASR is being recovered while microphone ASR remains healthy
- **THEN** microphone capture and transcript delivery continue without restarting the interview session

### Requirement: Transcript presentation separates lifecycle from visual grouping
The Web MUST reconcile transcript state by segment identity, revision, and terminal precedence before applying optional visual grouping. Joining adjacent text for readability MUST NOT make confirmed text active again or allow one source's draft to alter another source's terminal state.

#### Scenario: New partial follows adjacent final text
- **WHEN** a new partial from the same role begins within the visual join gap after a confirmed segment
- **THEN** the confirmed segment remains terminal and the partial is represented as a separate active draft lifecycle

#### Scenario: Reconnect replays duplicate events
- **WHEN** an SSE reconnect replays duplicate or out-of-order partial and final revisions
- **THEN** the visible transcript converges to one terminal segment without flicker or lifecycle regression

### Requirement: Recognition never answers without explicit user action
Realtime transcription, endpoint detection, watchdog recovery, and question identification MUST NOT create an answer task or consume answer points. Only the existing explicit quick-answer, screenshot-answer, or manual-input actions SHALL invoke answer generation.

#### Scenario: Interviewer question becomes final
- **WHEN** system-output ASR confirms a question and the user has not selected an answer action
- **THEN** the conversation updates but no answer task is created and no points are consumed

#### Scenario: User selects quick answer
- **WHEN** the user explicitly selects quick answer after an interviewer turn is available
- **THEN** the existing answer flow receives the latest eligible interviewer text exactly once

### Requirement: Commercial latency and reliability are observable and gated
The system MUST expose privacy-safe stage timings, finalization reasons, queue pressure, terminal acknowledgements, source recoveries, and stuck-turn counts without raw audio or transcript text. Release verification MUST exercise synthetic meeting noise, pauses, queue saturation, reconnect, and provider-timeout scenarios.

#### Scenario: Release candidate is evaluated
- **WHEN** the controlled performance and reliability suite runs against a release candidate
- **THEN** visible interim first text P95 is at most 1.5 seconds, detected stop-to-terminal P95 is at most 2.0 seconds and P99 at most 4.0 seconds, no active turn remains “转写中” beyond 8 seconds without an explicit terminal/degraded transition, and no terminal frame is lost

#### Scenario: Telemetry is inspected
- **WHEN** an operator inspects realtime metrics for a production session
- **THEN** the metrics identify the slow or recovered stage using identifiers, timings, counters, and error codes without exposing audio bytes or transcript content

### Requirement: Commercial rollout remains backward compatible and reversible
The backend and Web SHALL continue accepting the current production companion during the compatibility window. Adaptive desktop endpointing, backend watchdog enforcement, and terminal acknowledgement enforcement MUST be independently controllable for canary and rollback.

#### Scenario: Old companion joins after backend upgrade
- **WHEN** a currently supported companion without new optional terminal metadata starts an interview
- **THEN** realtime transcription continues through the compatible path and the backend watchdog can still resolve an abandoned partial

#### Scenario: Canary metrics regress
- **WHEN** latency, incomplete rate, CPU, queue depth, or source reconnect metrics exceed the release thresholds
- **THEN** operators can disable the affected new behavior without changing the ASR model, rolling back unrelated product features, or interrupting other active sources
