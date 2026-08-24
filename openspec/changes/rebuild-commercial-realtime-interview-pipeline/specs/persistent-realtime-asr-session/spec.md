## ADDED Requirements

### Requirement: One persistent provider session per active role
The ASR gateway SHALL maintain at most one provider connection for each enabled role channel in an active interview.

#### Scenario: Candidate channel begins streaming
- **WHEN** candidate audio first arrives for an active session
- **THEN** the gateway creates or resumes one candidate ASR connection and appends subsequent ordered audio to it

#### Scenario: Duplicate publisher metadata arrives
- **WHEN** repeated control messages describe the same role and session
- **THEN** the gateway reuses the current provider connection instead of creating another one

#### Scenario: Consecutive utterances use the same role connection
- **WHEN** one utterance is manually committed and finalized while the interview remains active
- **THEN** the next utterance on the same role appends to the existing provider WebSocket
- **AND** commit or final receipt alone does not close or recreate that connection

#### Scenario: Provider connection may be replaced
- **WHEN** the interview ends, the provider connection becomes unusable, an idle connection expires, or an unrecoverable provider error occurs
- **THEN** the gateway closes that role connection exactly once and creates a replacement only if the active interview still needs the channel

### Requirement: Correct realtime utterance lifecycle
The ASR adapter SHALL append streaming audio and SHALL use configured provider VAD or a complete client utterance commit; it MUST NOT treat each short PCM frame as an independent final recognition request.

#### Scenario: Continuous speech is received
- **WHEN** multiple short audio frames form one spoken utterance
- **THEN** they are appended to the same provider session and produce revision updates followed by one final utterance

#### Scenario: Input remains below the speech gate
- **WHEN** channel audio remains below the configured speech threshold
- **THEN** no standalone filler transcript is emitted solely from silent frames

#### Scenario: System audio uses independent endpointing
- **WHEN** system-output audio contains meeting background noise followed by short low-volume speech, English abbreviations, or digits
- **THEN** its independent noise floor, attack, release, minimum-speech and silence settings reject the background lead-in without dropping the meaningful short speech
- **AND** microphone VAD state and thresholds are neither read nor mutated by the system channel

### Requirement: Role-labelled normalized transcripts
The adapter SHALL normalize provider events into stable domain transcripts labelled `candidate` or `interviewer`, with segment identity, revision, timestamps, finality, and provider-neutral error state.

#### Scenario: Provider emits a final candidate transcript
- **WHEN** the candidate provider session finalizes an utterance
- **THEN** the gateway emits one final `candidate` transcript event with a stable segment identifier

#### Scenario: Provider emits a partial transcript
- **WHEN** the provider receive loop obtains a higher partial revision
- **THEN** the adapter immediately publishes that revision to the realtime transcript event path
- **AND** publication does not wait for another audio append, final, commit, stable-partial detection, or batch timer

### Requirement: Replaceable provider and recoverable failure
The system SHALL isolate Qwen-specific protocol details behind an ASR adapter and SHALL recover transient provider failures without duplicating final transcripts.

#### Scenario: Provider connection drops
- **WHEN** a provider WebSocket closes transiently during an active interview
- **THEN** the adapter reconnects with bounded backoff, exposes a degraded state, and resumes from current audio without replaying an acknowledged final transcript
