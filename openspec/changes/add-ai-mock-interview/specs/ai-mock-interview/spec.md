## ADDED Requirements

### Requirement: Independent mock interview navigation
The CN application SHALL show “模拟面试” immediately below “笔试模式” and SHALL provide separate creation, preparation, interaction and report views without replacing ordinary interview or written-exam flows. New default session titles and feature notices SHALL use the same name while retaining the AI interviewer identity disclosure.

#### Scenario: User opens the new entry
- **WHEN** an authenticated CN user clicks “模拟面试”
- **THEN** the mock interview entry explains the ten-question limit and creation pricing and offers creation or continuation of the user's own mock session

### Requirement: Idempotent per-session creation billing
The system MUST charge points users 100 points for successful creation plus 5 points per billable minute of mock interview time. Active time-pass members SHALL receive three free creations per business day, with both creation and minute fees waived for those quota-backed sessions. After all three free creations are used that day, the member MUST be charged 100 points per new creation plus 5 points per billable minute. Credit packages alone MUST NOT grant the free daily quota. The system MUST NOT add duplicate ordinary realtime-minute charges or separate per-answer, TTS-retry or report-retry fees.

#### Scenario: Points user creates a session
- **WHEN** a user without an active time pass has at least 100 available points and submits a valid creation request
- **THEN** the system creates one mock session and records one 100-point charge

#### Scenario: Active pass user has a free daily slot
- **WHEN** the authenticated user has an active time pass and fewer than three successful free creations in the applicable business day
- **THEN** exactly one free daily slot is consumed and the resulting session has zero creation and minute fees

#### Scenario: Active pass user exhausts the daily quota
- **WHEN** the member has used all three free creations and explicitly confirms another paid creation
- **THEN** the new session costs 100 points to create plus 5 points per billable minute despite the membership remaining active

#### Scenario: Duplicate creation request
- **WHEN** identical creation requests with the same owner-scoped idempotency key arrive concurrently or are retried after a lost response
- **THEN** at most one session and one charge are created and the original result can be recovered

#### Scenario: Creation cannot complete
- **WHEN** balance is insufficient or atomic session creation fails
- **THEN** no usable unpaid session or settled orphan charge is left behind and the user sees an actionable error

### Requirement: Atomic daily member creation quota
The system MUST enforce the three-free-creation quota by authenticated owner and server-determined business date, atomically with creation and idempotency. Failed creation MUST NOT consume a slot, retries MUST NOT consume additional slots, and deleting history MUST NOT restore daily quota. The business day SHALL reset at midnight in Asia/Shanghai, as approved by the user, and this rule MUST be user-visible. An exhausted free quote MUST NOT silently become a paid charge.

#### Scenario: Concurrent requests for the last free slot
- **WHEN** two different creation requests compete for the owner's final free slot
- **THEN** at most one gets that slot and any request whose free price is no longer valid requires explicit paid confirmation before deducting points

#### Scenario: Next business day
- **WHEN** the server crosses the approved daily reset boundary and the user still has an active time pass
- **THEN** the user can receive three free creations in the new day's quota without rewriting prior usage or repricing existing sessions

#### Scenario: Cross-day idempotent retry
- **WHEN** a successful creation request from the previous day is retried with the same owner-scoped idempotency key
- **THEN** it returns the original session and does not consume a slot from the new day or charge again

#### Scenario: History record is deleted
- **WHEN** an owner deletes one of the at-most-two saved records
- **THEN** the history storage slot is freed but the successful creation remains counted in its original day's free quota

### Requirement: Idempotent minute usage billing
The system SHALL apply the confirmed standard rate of 5 points per started cumulative minute of speaking/listening interaction to paid sessions and MUST NOT debit the same session billing interval more than once. Only a valid session-level daily-free entitlement SHALL waive minute fees; the existence of an active time pass alone MUST NOT waive fees for the fourth or later session after quota exhaustion. The billing class SHALL be locked at creation, even across midnight or membership expiry. It MUST stop accrual when the session ends or expires; preparation, provider generation waits, pause, disconnected time and report generation/viewing/saving MUST NOT generate minute fees. Resuming SHALL use any remaining previously paid minute rather than starting a fresh charge.

#### Scenario: Pause and resume within a paid minute
- **WHEN** a paid session uses 25 seconds, pauses and later uses another 35 seconds
- **THEN** it has used one cumulative minute with one 5-point debit, and only continuing beyond that minute requires another debit

#### Scenario: Control connection is lost
- **WHEN** the active control connection disconnects or its lease expires
- **THEN** audio eligibility closes, unconfirmed offline time is not added, and a reconnect cannot back-bill the gap

#### Scenario: Billable minute for a points user
- **WHEN** a paid session incurs one additional billable minute under the approved timing policy
- **THEN** exactly one 5-point usage entry is settled independently of the one-time creation fee

#### Scenario: Meter is retried or resumed
- **WHEN** a worker, browser or reconnect path submits the same session billing interval again
- **THEN** it recovers the existing usage result without a second deduction

#### Scenario: Interview finishes
- **WHEN** the mock session ends and report processing continues
- **THEN** no additional interview minute accrues during report processing or later history access

#### Scenario: Insufficient minute balance
- **WHEN** the owner of a paid session cannot fund the next chargeable interval
- **THEN** continuing chargeable interaction is blocked with an actionable balance message and already completed answers remain recoverable within the approved retention policy

### Requirement: Required owner resume and desktop preparation

The feature MUST work with the shipped WebSocket v2 microphone-capable companion without requiring a new mock-specific companion release. The backend SHALL isolate mock frames from ordinary answers and billing. The UI MUST disclose that legacy capture may continue during question playback while the server discards non-answer audio without transcribing or storing it.

#### Scenario: Existing assistant starts only after the session goes live
- **WHEN** an authorized existing assistant with microphone permission is bound during preparation
- **THEN** the user can start without a mock-specific capability flag
- **AND** waiting for its audio channel does not start answer-minute billing

#### Scenario: Shipped companion heartbeat reports unknown permission
- **WHEN** a fresh, correctly bound shipped v2 assistant reports microphone permission as unknown or omits it, without a mock-specific protocol flag
- **THEN** preparation permits starting with a truthful notice that permission is verified by the local assistant, rather than claiming permission granted
- **AND** microphone access remains OS-enforced and answering requires its authenticated audio channel; waiting for that channel accrues no answer time and retrying the same session does not repeat the entry charge

#### Scenario: Preparation cannot proceed
- **WHEN** microphone permission is explicitly denied/restricted, the device is offline, its binding is invalid, or its protocol is incompatible
- **THEN** the start action remains blocked with an actionable preparation reason, rather than an indefinite generic waiting status

#### Scenario: Legacy delayed frames cannot enter a new round
- **WHEN** a legacy frame was captured before the current answer window, is a duplicate, uses the system channel, or arrives after revocation
- **THEN** it is discarded without ordinary ASR, quick-answer tasks or ordinary billing
- **AND** clock anomalies or connection loss pause answering with an actionable message rather than silently assigning audio to the next question
The system MUST require a selected and explicitly confirmed ready resume belonging to the authenticated user, an available parsed version, a valid authorized machine-code binding and microphone permission before starting mock interview audio. It MUST reject bypass through ordinary session start or restart endpoints.

#### Scenario: Resume or device is unavailable
- **WHEN** the resume is unselected, still processing, deleted, belongs to another user, has unreadable parsed content, or the device is unavailable
- **THEN** starting is blocked with an appropriate recovery action and no question or audio capture begins

#### Scenario: Preparation completes
- **WHEN** the user confirms the selected resume version and connects a compatible authorized desktop assistant with microphone permission
- **THEN** the paid mock session can start using only that resume version and microphone audio

### Requirement: Resume-grounded bounded question generation
The text-generation model SHALL produce one interview question at a time based on the selected resume, optional target role and previously submitted answers. All follow-up questions SHALL count toward a server-enforced maximum of ten published questions. Resume and answer content MUST be treated as untrusted evidence, never as instructions that override the interview policy.

#### Scenario: Follow-up after an answer
- **WHEN** the user submits a completed answer to the current question
- **THEN** the next question can probe that answer or a relevant resume topic without inventing experiences or presenting another user's material

#### Scenario: Tenth answer is submitted
- **WHEN** the user submits an answer to the tenth question
- **THEN** the system proceeds to report generation and never emits an eleventh question

#### Scenario: Prompt injection in a resume
- **WHEN** a resume or candidate answer asks the model to ignore the limit, disclose secrets or assign a fabricated score
- **THEN** the system retains question limits, privacy restrictions and evidence-based assessment

### Requirement: Explicit answer completion and recoverable rounds
The system MUST advance only when the user explicitly clicks “回答完成” for the current round. It MUST enforce round identity, single in-flight advancement and idempotency on the server, preserve recoverability after a page refresh and reject stale or cross-owner operations.

#### Scenario: Candidate pauses to think
- **WHEN** the microphone becomes silent during the answer
- **THEN** the system keeps the current question open without automatically advancing

#### Scenario: Duplicate answer submission
- **WHEN** the same current-round answer is submitted twice or by two tabs concurrently
- **THEN** only one answer is accepted and at most one next question is generated

#### Scenario: No answer is available
- **WHEN** the user clicks “回答完成” with no confirmed answer text
- **THEN** the system explains that an answer is needed and permits continuing or explicitly ending, without fabricating a response

### Requirement: Dedicated Qwen realtime question speech
Question speech SHALL use the server-side `qwen3-tts-instruct-flash-realtime` adapter with a supported voice and endpoint. TTS MUST synthesize the validated question text rather than generate interview content. API keys MUST remain on the server and each stream MUST be authenticated to the session owner and bounded in duration, buffering and concurrency.

#### Scenario: Question is spoken
- **WHEN** a question is published and speech synthesis succeeds
- **THEN** the question text and matching incremental audio are presented, and the AI interviewer visibly switches from speaking to listening when playback ends

#### Scenario: Synthesis fails
- **WHEN** the TTS provider times out or rejects the request
- **THEN** the question text remains available, an explicit retry or text-continuation choice is shown, no new fee or question is created, and the failed stream is closed

### Requirement: Microphone turn isolation
Mock interviews MUST use microphone input only and MUST NOT route candidate answers into ordinary quick-answer generation. The backend MUST exclude interviewer playback and its delayed recognition from candidate answers and report evidence using authoritative round and capture-window boundaries.

#### Scenario: Interviewer audio plays through speakers
- **WHEN** the AI interviewer is speaking or replaying a question
- **THEN** microphone echo from that playback is excluded from candidate answer collection and does not trigger another question or ordinary quick answer

#### Scenario: Late transcript from previous round
- **WHEN** a delayed transcript belongs to a speaking window or an older capture epoch
- **THEN** it is discarded rather than appended to the current answer

### Requirement: Evidence-based report and scoring
The report SHALL include overall and dimension scores, per-question feedback and actionable answer suggestions based on submitted answers and selected resume evidence. It MUST distinguish evidence, inference and suggestions, label AI assessments as practice feedback, and MUST NOT infer sensitive personal traits or guarantee hiring outcomes.

#### Scenario: Session completes with answers
- **WHEN** ten answers have been submitted or the user explicitly ends after at least one valid answer
- **THEN** a full or clearly labeled partial report is generated from those answers with traceable question-level feedback

#### Scenario: Session ends without evidence
- **WHEN** the session ends without a valid answer
- **THEN** the report indicates insufficient evidence and does not manufacture a numerical assessment

### Requirement: Download completed report as Word
The completed mock report view SHALL offer “下载 Word” when report data is available. It SHALL generate an editable `.docx` locally from the authenticated owner's loaded report, including session name, target role, full or partial status, overall and dimension scores, summary, every question and submitted answer, evidence, strengths, improvements, answer suggestions and practice priorities. It MUST preserve insufficient-evidence and unanswered states and the AI practice-feedback disclosure. Export MUST NOT invoke a model, change billing or storage quotas, or include raw audio, a full resume copy, internal identifiers or credentials. The Word dependency SHALL load only on demand. Export SHALL preserve long and multiline text, use a safe filename, prevent concurrent downloads and provide retryable errors.

#### Scenario: Owner downloads a completed report
- **WHEN** the owner clicks “下载 Word” on an available completed report
- **THEN** the browser downloads a standards-compliant editable Word document matching that report without an extra fee, save or backend request

#### Scenario: Report is partial or has insufficient answers
- **WHEN** a partial or insufficient-evidence report is downloaded
- **THEN** the document retains its partial status, null scores are not replaced with zero, and unanswered questions are explicitly marked without fabricated feedback

#### Scenario: Report is unavailable or export fails
- **WHEN** the report is still generating or missing
- **THEN** a download action is not offered
- **WHEN** an export is in progress or fails
- **THEN** duplicate clicks cannot start another export, failure leaves the report intact and the user can retry

### Requirement: Explicit retention and resource cleanup
The feature MUST NOT persist raw audio or log resume/transcript bodies. Transcript and report retention MUST follow an explicitly approved product policy before implementation is released; the default MUST NOT introduce unapproved persistent personal-data storage. Session completion, cancellation, expiry, disconnect cleanup and shutdown MUST close ASR/TTS resources and remove transient session buffers.

#### Scenario: Session ends during synthesis
- **WHEN** the user ends a session while a question or audio stream is being generated
- **THEN** generation and playback are cancelled, capture is stopped, late results cannot revive the session and temporary buffers are released

#### Scenario: Repeated sessions finish
- **WHEN** multiple synthetic mock interviews complete consecutively
- **THEN** active provider connections, worker tasks and session-scoped caches return to their expected idle bounds rather than growing with each ended session

### Requirement: Two saved mock records per owner
The system MUST automatically save each ended session's report and confirmed question-answer content and enforce an account-wide maximum of two records, including for time-pass members. Creation atomically reserves a storage slot before charging so completion never depends on remaining capacity. In-progress sessions occupy their reserved slot. The quota is not a daily or lifetime creation limit. Old records MUST NOT be deleted or overwritten without explicit user action. Audio and full resume copies MUST NOT be retained in history.

#### Scenario: Third record is requested
- **WHEN** an owner has two saved or in-progress records and attempts to create another
- **THEN** the server rejects creation before charging and explains how to free a slot without deleting either record

#### Scenario: Concurrent saves use the last slot
- **WHEN** an owner has one saved record and two different sessions are saved concurrently
- **THEN** at most one additional record is saved and the total never exceeds two

#### Scenario: Duplicate save and explicit deletion
- **WHEN** the same session is saved again or the owner explicitly deletes an existing saved record
- **THEN** duplicate saving consumes no extra slot and successful deletion frees a slot without deleting the financial ledger

#### Scenario: Full history does not prevent completion
- **WHEN** a user finishes a mock interview whose slot was reserved at creation
- **THEN** the interview ends and saves in its existing slot without requiring deletion of another record

### Requirement: Fault compensation
Failed creation MUST NOT charge or consume daily quota. User cancellation after successful creation MUST NOT refund the entry fee. A verified terminal system/provider fault before any answer was completed MUST refund this session's debited points or restore its daily free quota exactly once. Clients MUST NOT be able to claim a fault to obtain a refund.

#### Scenario: Retry compensation
- **WHEN** fault compensation is retried or races another worker
- **THEN** only one financial refund or quota restoration occurs, with the original ledger preserved

### Requirement: Audio-driven interviewer playback indicator
The workbench MUST show a compact waveform below the interviewer portrait. Its bar heights MUST follow audio actually playing in the browser, not provider waiting time, microphone input or a simulated timer. Audible playback SHALL show “面试官正在提问”. Silence SHALL not produce artificial moving bars. Pause, playback completion, playback failure, disconnection and unmount MUST stop visualization and release its animation loop. Reduced-motion preferences MUST retain a readable static playback status without moving bars. This indicator MUST NOT change capture gating, billing, provider calls or store audio.

#### Scenario: Played audio drives the bars
- **WHEN** question PCM is played and its volume changes
- **THEN** the portrait waveform responds to that playback and not the user's microphone; waiting for the first audio does not animate it

#### Scenario: Playback stops or motion is reduced
- **WHEN** playback stops, the buffer drains, or the page closes
- **THEN** the bars return to their idle baseline immediately and no animation loop remains; reduced-motion users see only static bars and an accurate text status

### Requirement: Backward-compatible local delivery
The feature MUST preserve existing ordinary and mobile interview, written-exam, billing and desktop behavior. Implementation and tests SHALL remain local until a separate deployment authorization is given; missing real-device or provider tests MUST be reported rather than counted as passed.

#### Scenario: Existing interview regression
- **WHEN** the feature is disabled or a user starts an ordinary interview or written exam
- **THEN** its existing navigation, billing, audio routing and answer behavior remain unchanged

#### Scenario: Authorized CN release
- **WHEN** automated and real-provider checks have passed, the user explicitly authorizes deployment followed by their real-device test, and CN has no active interviews
- **THEN** CN deployment can proceed using the verified production baseline, with health checks and rollback readiness; real-microphone acceptance remains explicitly pending and MUST NOT be reported as passed
