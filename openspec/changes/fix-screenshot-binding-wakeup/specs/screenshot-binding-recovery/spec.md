## ADDED Requirements

### Requirement: Screenshot stream follows authoritative binding identity
The Companion SHALL publish the authoritative screenshot binding identity independently of capture state, and the main process SHALL use that identity to own the screenshot request stream.

#### Scenario: Binding appears while capture state is unchanged
- **WHEN** the screenshot stream is suspended, capture state remains `capturing`, and a successful pairing poll reports a valid binding
- **THEN** the Companion restarts the screenshot request stream without requiring window activation or a capture-state transition

#### Scenario: Binding identity changes
- **WHEN** a successful pairing poll reports a different `sessionId + bindingId`
- **THEN** the Companion cancels the previous stream generation and starts exactly one stream for the new binding

### Requirement: Duplicate lifecycle notifications preserve one owner
The Companion SHALL ignore repeated notifications for the same valid binding while its screenshot stream is healthy.

#### Scenario: Poll repeats the same binding
- **WHEN** consecutive successful pairing polls publish the same binding identity and the stream is not suspended
- **THEN** the current stream remains active and no duplicate stream owner is created

### Requirement: Missing bindings recover without a request storm
The Companion SHALL suspend screenshot streaming after a missing registration or no-live-binding admission response and SHALL rely on bounded authoritative binding polls to resume it.

#### Scenario: Temporary no-live-binding response
- **WHEN** screenshot admission returns HTTP 409
- **THEN** the stream suspends without continuous SSE retries and resumes on the next valid binding notification

#### Scenario: Device registration is absent
- **WHEN** screenshot admission returns HTTP 404 and pairing state confirms no registered device or binding
- **THEN** the stream remains stopped until authoritative pairing state reports a valid binding

### Requirement: Existing product chains remain unchanged
The binding recovery change SHALL NOT alter audio capture, ASR, transcript rendering, answer generation, screenshot upload or billing behavior.

#### Scenario: Existing interview and written-exam flows run
- **WHEN** a user uses interview audio features or submits a screenshot request
- **THEN** all existing contracts and charging rules remain unchanged except that screenshot stream recovery is bounded by the binding poll interval
