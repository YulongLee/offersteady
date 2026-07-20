## ADDED Requirements

### Requirement: Authenticated long-lived transport
The desktop SHALL stream realtime audio through a versioned, authenticated, long-lived connection scoped to one user, device, and active interview.

#### Scenario: Transport connects
- **WHEN** a paired desktop presents a valid short-lived transport token
- **THEN** the gateway accepts one connection and negotiates protocol version, codec, channels, and resume offsets

#### Scenario: Token is invalid
- **WHEN** a desktop presents an expired, revoked, or mismatched token
- **THEN** the gateway rejects the connection without starting capture-side retry loops for a terminal authorization failure

### Requirement: Ordered multiplexed audio
The transport SHALL carry independently sequenced microphone and system-output messages and SHALL acknowledge the highest contiguous sequence per channel.

#### Scenario: Frames arrive in order
- **WHEN** valid channel frames arrive with contiguous sequences
- **THEN** the gateway forwards them in order and advances that channel acknowledgement

#### Scenario: A sequence gap occurs
- **WHEN** the gateway receives a frame beyond the next expected sequence
- **THEN** it reports the gap and does not silently reorder the channel across an unacknowledged hole

### Requirement: Bounded backpressure
The desktop and gateway SHALL enforce finite queues and SHALL prevent producer rate from creating unbounded requests, sockets, tasks, or memory.

#### Scenario: Provider processing slows
- **WHEN** ASR consumption is slower than audio arrival
- **THEN** the gateway applies backpressure and drops superseded interim data before final utterance data while queue duration remains at or below two seconds

#### Scenario: Server is unavailable
- **WHEN** reconnect attempts are in progress
- **THEN** only one attempt is active, retries use bounded jittered backoff, and connection count remains bounded

### Requirement: Resume after transient disconnect
The desktop SHALL reconnect with the last acknowledged sequence and SHALL replay only unacknowledged audio still present in its bounded buffer.

#### Scenario: Short network interruption
- **WHEN** connectivity returns before buffered audio expires
- **THEN** transport resumes without duplicate accepted sequences

#### Scenario: Buffer window expires
- **WHEN** connectivity returns after old audio has been dropped
- **THEN** transport resumes from current audio and emits an explicit gap event
