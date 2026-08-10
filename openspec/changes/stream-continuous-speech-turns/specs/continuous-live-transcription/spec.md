## ADDED Requirements

### Requirement: Continuous speech streams as stable revisions
The companion MUST upload active speech incrementally and MUST retain one stable segment identity through ordinary breathing or thinking pauses until a meaningful source-specific turn boundary is reached.

#### Scenario: Candidate speaks with short pauses
- **WHEN** microphone speech contains pauses shorter than the configured candidate turn boundary
- **THEN** interim transcript revisions update the same segment and Web conversation turn instead of creating new confirmed cards

#### Scenario: Interim text grows
- **WHEN** ASR produces additional text for an active segment
- **THEN** the system publishes a higher revision and the Web replaces the visible text for that turn without waiting for finalization

### Requirement: Finalization is responsive and bounded
The companion SHALL use source-specific silence boundaries and MUST enforce a maximum active-segment duration so continuous streaming does not create unbounded audio buffers.

#### Scenario: Candidate finishes a sentence
- **WHEN** microphone speech remains below the continuation threshold for the candidate silence boundary
- **THEN** the current segment is finalized once and the next speech starts a new segment

#### Scenario: Interviewer finishes a question
- **WHEN** trusted system audio remains below the continuation threshold for the shorter interviewer silence boundary
- **THEN** the current interviewer segment is finalized without waiting for the longer candidate boundary

#### Scenario: Uninterrupted speech reaches the bound
- **WHEN** an active segment reaches the configured maximum duration while speech continues
- **THEN** the companion finalizes that bounded segment and continues subsequent audio in a new segment without unbounded memory growth

### Requirement: Conversation turns safely reconcile residual fragments
The Web SHALL project adjacent transcript fragments into one conversation turn only when they share a trusted role, are close in time, do not conflict or overlap, and remain within bounded turn limits.

#### Scenario: Older companion sends adjacent candidate fragments
- **WHEN** consecutive final candidate fragments arrive within the safe join window
- **THEN** the Web displays their ordered text in one candidate turn while retaining every contributing source segment ID

#### Scenario: Role changes
- **WHEN** a candidate fragment is followed by an interviewer fragment
- **THEN** the Web keeps them as separate conversation turns regardless of timing

#### Scenario: Long pause separates sentences
- **WHEN** same-role fragments are separated by more than the safe join window
- **THEN** the Web displays separate confirmed turns

### Requirement: Automatic questions use complete trusted interviewer context
The system MUST build question text from the latest eligible final system-audio turn and MUST NOT include microphone speech or an unresolved overlapping fragment.

#### Scenario: Interviewer gives context before the question
- **WHEN** adjacent trusted interviewer fragments form one bounded turn ending in a complete high-confidence question
- **THEN** the answer pipeline receives the combined interviewer context as one question and creates at most one answer trigger

#### Scenario: Candidate speech follows the question
- **WHEN** the candidate begins a new final microphone turn
- **THEN** earlier interviewer fragments are not joined into a later question after that boundary

### Requirement: Continuous transcription preserves privacy and compatibility
The change MUST keep raw PCM in bounded volatile memory, MUST preserve existing realtime protocol compatibility, and MUST use only synthetic or explicitly authorized transcript fixtures for verification.

#### Scenario: Session ends
- **WHEN** a live interview session is stopped or retired
- **THEN** active audio buffers and temporary turn state are cleared without adding raw-audio persistence

#### Scenario: Existing companion remains installed
- **WHEN** an older compatible companion sends valid revision and final fields
- **THEN** Backend and Web continue to accept the messages and apply safe display reconciliation
