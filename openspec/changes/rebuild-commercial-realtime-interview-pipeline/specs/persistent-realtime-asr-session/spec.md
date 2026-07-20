## ADDED Requirements

### Requirement: One persistent provider session per active role
The ASR gateway SHALL maintain at most one provider connection for each enabled role channel in an active interview.

#### Scenario: Candidate channel begins streaming
- **WHEN** candidate audio first arrives for an active session
- **THEN** the gateway creates or resumes one candidate ASR connection and appends subsequent ordered audio to it

#### Scenario: Duplicate publisher metadata arrives
- **WHEN** repeated control messages describe the same role and session
- **THEN** the gateway reuses the current provider connection instead of creating another one

### Requirement: Correct realtime utterance lifecycle
The ASR adapter SHALL append streaming audio and SHALL use configured provider VAD or a complete client utterance commit; it MUST NOT treat each short PCM frame as an independent final recognition request.

#### Scenario: Continuous speech is received
- **WHEN** multiple short audio frames form one spoken utterance
- **THEN** they are appended to the same provider session and produce revision updates followed by one final utterance

#### Scenario: Input remains below the speech gate
- **WHEN** channel audio remains below the configured speech threshold
- **THEN** no standalone filler transcript is emitted solely from silent frames

### Requirement: Role-labelled normalized transcripts
The adapter SHALL normalize provider events into stable domain transcripts labelled `candidate` or `interviewer`, with segment identity, revision, timestamps, finality, and provider-neutral error state.

#### Scenario: Provider emits a final candidate transcript
- **WHEN** the candidate provider session finalizes an utterance
- **THEN** the gateway emits one final `candidate` transcript event with a stable segment identifier

### Requirement: Replaceable provider and recoverable failure
The system SHALL isolate Qwen-specific protocol details behind an ASR adapter and SHALL recover transient provider failures without duplicating final transcripts.

#### Scenario: Provider connection drops
- **WHEN** a provider WebSocket closes transiently during an active interview
- **THEN** the adapter reconnects with bounded backoff, exposes a degraded state, and resumes from current audio without replaying an acknowledged final transcript
