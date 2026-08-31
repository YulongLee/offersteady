## ADDED Requirements

### Requirement: Automatic answer is an explicit session setting
The system SHALL expose an automatic-answer switch on the live interview page, MUST keep it disabled by default for every new session, and MUST persist its value and most recent activation time on the owned session. Turning it off MUST prevent future automatic submissions without cancelling an answer that is already running. Manual quick answer and screenshot answer MUST remain available regardless of the switch value.

#### Scenario: New session keeps existing manual behavior
- **WHEN** a user enters a newly created live interview and does not enable automatic answer
- **THEN** no answer task is created from speech alone and the existing quick-answer and screenshot actions behave as before

#### Scenario: User enables automatic answer
- **WHEN** the owner enables the switch during a live interview
- **THEN** the server stores the enabled state and activation time and the page may consume only eligible questions at or after that time

#### Scenario: User disables automatic answer during generation
- **WHEN** the owner disables the switch while an automatic answer is already streaming
- **THEN** the current answer is allowed to finish and no later question is automatically submitted

### Requirement: Automatic answers use stable interviewer questions only
The system MUST automatically submit only a final, high-confidence, confirmed question candidate produced from the interviewer system-audio source after the current activation time. It MUST NOT automatically submit ASR partials, candidate microphone speech, low-confidence candidates, historical candidates, echo-like content, or candidates from an ambiguous or degraded source.

#### Scenario: Confirmed interviewer question arrives
- **WHEN** automatic answer is enabled and a new system-audio question candidate reaches the existing high-confidence confirmed state
- **THEN** the page submits that frozen candidate through the live answer API

#### Scenario: Partial or candidate speech arrives
- **WHEN** ASR emits partial text or final text from the user's microphone
- **THEN** the transcript may update but no automatic answer task is created

#### Scenario: Old candidate is present when enabled
- **WHEN** automatic answer is enabled after one or more confirmed candidates already exist
- **THEN** those candidates are not automatically answered

### Requirement: Each candidate creates at most one automatic answer
Before creating an automatic answer, the backend MUST verify session ownership, live status, enabled state, activation boundary and candidate eligibility, and MUST claim the candidate using its stable identifier. Concurrent or repeated requests for the same candidate MUST NOT create or bill another answer task. The page MUST keep at most one live answer generation active at a time.

#### Scenario: Two pages submit the same candidate
- **WHEN** concurrent automatic requests reference the same eligible candidate
- **THEN** at most one request creates and bills an answer task and the other is rejected as already claimed

#### Scenario: Another question arrives during generation
- **WHEN** a confirmed question arrives while an answer task is still generating
- **THEN** the current task is not interrupted and the page does not run two answer streams concurrently

### Requirement: Automatic answers reuse the existing answer pipeline
An accepted automatic answer MUST use the same frozen-question handling, interview language, programming language, confirmed material snapshot, retrieval, prompt, model, streaming response, persistence, billing, cancellation and answer presentation as manual quick answer. The implementation MUST distinguish the trigger as `auto` for operational events without logging additional raw audio or question content.

#### Scenario: English programming interview auto-answers
- **WHEN** an English session with a selected programming language automatically submits an eligible coding question
- **THEN** the existing English and programming settings are applied exactly as they are for manual quick answer

#### Scenario: Automatic answer lacks entitlement
- **WHEN** the current user lacks the entitlement required by the existing live answer pipeline
- **THEN** the existing server-side billing guard rejects the task without bypass or duplicate charge and manual controls remain usable

### Requirement: Runtime degradation stops automatic triggering safely
The page MUST stop starting automatic answers when the session is not live, capture is paused, the active-page lease is replaced, the interviewer source is unavailable, or the page is shutting down. These conditions MUST NOT erase visible transcripts or answers and MUST NOT disable manual recovery actions solely because automatic mode is unavailable.

#### Scenario: Active page lease is replaced
- **WHEN** another page becomes the authoritative live interview page
- **THEN** the replaced page starts no further automatic answer requests and preserves already displayed content

#### Scenario: Interviewer channel degrades
- **WHEN** the runtime can no longer distinguish a valid interviewer system-audio source
- **THEN** automatic triggering pauses while manual question and screenshot paths remain available
