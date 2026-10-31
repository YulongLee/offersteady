## ADDED Requirements

### Requirement: Distinguish pending microphone status from denied permission
CN mock preparation SHALL distinguish missing, unknown or unrecognized microphone status from explicit denied/restricted permission. Dedicated mock assistants with unconfirmed permission MUST remain blocked without claiming OS denial or changing the stored permission. Fresh granted permission SHALL allow existing readiness checks to succeed. Legacy v2 deferred compatibility SHALL remain limited to its existing scope.

#### Scenario: Initial dedicated assistant heartbeat is unknown
- **WHEN** a fresh correctly bound mock protocol 1 assistant reports unknown or missing permission
- **THEN** preparation reports `mock_microphone_checking`, remains not ready and neither starts generation/capture nor rewrites permission

#### Scenario: Permission result arrives later
- **WHEN** the existing assistant subsequently reports granted and the current page receives a normal heartbeat state
- **THEN** readiness becomes true in the same session with its selected resume, binding and creation charge preserved

#### Scenario: Explicit denial or invalid device
- **WHEN** permission is denied/restricted or the device is stale, unbound, belongs to another owner or has the wrong device/generation
- **THEN** the appropriate permission or connection error remains blocking, including at start and microphone attach

### Requirement: Recover preparation in place without extra polling
The mock page SHALL refresh preparation through the existing control heartbeat and SHALL offer a throttled explicit recheck without creating or rebinding a session. Unknown status SHALL show a checking message and after thirty seconds SHALL show actionable unconfirmed-status guidance instead of indefinite checking or an authorization accusation. The page MUST NOT automatically start, reopen capture, change deadline or charge during recovery.

#### Scenario: User checks again
- **WHEN** the connected preparing page receives unknown/denied status and the user clicks recheck
- **THEN** it sends one existing heartbeat, retains the same resume/session/binding and makes no creation/start/provider request

#### Scenario: Waiting expires or page leaves
- **WHEN** unknown persists for thirty seconds or the page disconnects, changes session or unmounts
- **THEN** timeout guidance appears only for the current connected preparation and stale timers cannot modify the replacement page

#### Scenario: Pending start error recovers
- **WHEN** a start attempt receives a microphone readiness error and a later authoritative state reports ready
- **THEN** the stale permission error clears while unrelated errors remain visible and no automatic start occurs

### Requirement: Keep browser playback recovery separate and fenced
Mock question playback SHALL identify browser sound playback restrictions separately from assistant microphone permission. Audio unlock SHALL succeed only for the current running context within a bounded wait. Explicit user recovery SHALL remain possible after failure. Stale or duplicate asynchronous playback operations MUST NOT send speak/listen/start after their connection, question, phase or user intent has changed.

#### Scenario: Browser requires a click or resume fails
- **WHEN** a restored question cannot unlock playback automatically or resume resolves without a running context
- **THEN** the page identifies browser sound recovery, offers a clickable retry and does not report microphone denial or start listening automatically

#### Scenario: Auto and manual unlock race
- **WHEN** an automatic unlock and a user retry resolve in either order for the same question
- **THEN** at most one current speak command is sent and rejected or timed-out work leaves a usable retry button

#### Scenario: Question or connection changes before unlock completes
- **WHEN** the user skips, pauses, ends, disconnects or moves to another question/session while unlock is pending
- **THEN** a late result cannot play, start or listen in the replacement state

#### Scenario: Playback is interrupted after all chunks have arrived
- **WHEN** the current browser audio context becomes suspended or interrupted with queued question audio and no more incoming PCM
- **THEN** playback stops, the current question pauses with concise recovery guidance and explicit continue/retry remains usable without starting listening or affecting a replacement context

#### Scenario: End overtakes the local microphone settling timer
- **WHEN** the user ends or pauses while the local post-playback timer is pending and the server response is delayed
- **THEN** the timer and pending listen intent are immediately cancelled and no later listen command is sent

#### Scenario: A selection response arrives after navigation or completion
- **WHEN** a resume-selection or binding operation resolves after the page changes session/connection lifecycle or the authoritative session has advanced past that response
- **THEN** the old response cannot overwrite the active session, roll back its phase/version or trigger commands on its replacement, and the current page remains operable

### Requirement: Restrict changes to mock interview and local verification
This change SHALL leave desktop packages, normal/written interview, materials/resume optimization, Global edition, prompts/providers, billing and deadlines unchanged. Validation SHALL use synthetic data without actual audio or paid provider calls. Deployment SHALL require a later user instruction.

#### Scenario: Existing feature or billing regression
- **WHEN** relevant regression suites run with the change
- **THEN** existing mock creation idempotency, daily free quota, flat fee, sixty-minute deadline, answer isolation and unrelated navigation retain their behavior

### Requirement: Keep preparation instructions concise
The mock preparation page SHALL keep its main area focused on resume selection, machine code, current status and actions. Supplemental companion and audio handling instructions SHALL appear in a closed-by-default disclosure below the start action. Recovery notices SHALL use concise actionable wording and the AI interviewer identity SHALL remain visible. This presentation update MUST NOT alter readiness or recovery behavior.

#### Scenario: Preparation first opens
- **WHEN** the user opens mock preparation
- **THEN** long companion/audio explanatory paragraphs do not appear above the actions, a collapsed 使用说明 remains available below start, and current status and recovery actions remain usable
