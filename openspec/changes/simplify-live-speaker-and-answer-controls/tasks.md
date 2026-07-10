## 1. Reconcile Active Specifications and Guidance

- [x] 1.1 Revise `add-speaker-role-detection` proposal, specs and design to use source-fixed `我/面试官` roles and remove user-visible unknown-role confirmation
- [x] 1.2 Remove or supersede active speaker-detection tasks for mixed-audio role guessing, role confidence UI and role correction while retaining echo, transcript, boundary and trigger evaluation tasks
- [x] 1.3 Revise `add-desktop-audio-companion` start-control scenarios and design from “开始收音” to “开始面试” without weakening explicit permission or visible-capture requirements
- [x] 1.4 Reconcile `add-web-interview-application`, `refine-interview-materials-and-mobile-actions` and other active live-workspace artifacts that still require role-pending controls
- [x] 1.5 Update `docs/user-journey.md`, relevant privacy guidance and in-app usage guidance with two-role routing, safe audio degradation and answer termination behavior
- [x] 1.6 Strictly validate every reconciled active change before changing implementation behavior

## 2. Protocol and Compatibility Model

- [x] 2.1 Define the new dual-channel transcript contract so microphone/headset maps to candidate and system audio maps to interviewer
- [x] 2.2 Stop new protocol fixtures and clients from creating a user-visible `unknown` role while retaining a bounded legacy decoder path
- [x] 2.3 Define source-degraded events for missing, mixed, disconnected and incompatible audio inputs without inventing a third role
- [x] 2.4 Add `queued`, `generating`, `completed`, `failed` and `cancelled` answer-task states with monotonic revision rules
- [x] 2.5 Add a session-scoped, versioned and idempotent cancel-answer command and authoritative cancellation result
- [x] 2.6 Add protocol tests for role routing, legacy unknown isolation, state transitions, stale revisions and duplicate cancellation commands
- [x] 2.7 Update protocol compatibility declarations so older Web or desktop clients degrade safely rather than mislabelling audio

## 3. Dual-Channel Role and Question Routing

- [x] 3.1 Replace inferred role mapping in the supported dual-channel path with deterministic source routing
- [x] 3.2 Preserve stable source IDs, transcript revisions and optional anonymous speaker IDs for ordering and deduplication without exposing extra roles
- [x] 3.3 Run cross-channel echo and duplicate suppression before system-audio question triggering
- [x] 3.4 Restrict automatic question confirmation to final, complete, unique system-audio questions
- [x] 3.5 Prevent microphone/headset statements, clarification questions and duplicate echoes from creating answer tasks or billing reservations
- [x] 3.6 Implement missing, mixed and disconnected-source degradation that keeps manual questioning available and existing session state intact
- [x] 3.7 Clear temporary audio buffers and echo-matching features when the interview ends
- [x] 3.8 Add synthetic service tests for clean dual channel, multiple remote speakers, echo, overlap, mixed input, source loss and reconnect

## 4. Two-Role Live Conversation UI

- [x] 4.1 Render every supported local-input segment as “我” and every supported system-audio segment as “面试官”
- [x] 4.2 Remove “角色待确认”, numbered interviewer roles, role confidence text and role-correction buttons from `ConversationMonitor`
- [x] 4.3 Render source-level degraded states outside the role-labelled transcript list with a manual-question recovery path
- [x] 4.4 Preserve transcript revision replacement, chronological ordering, scroll intent and responsive state during source updates
- [x] 4.5 Replace synthetic Web fixtures that contain unknown roles with source-valid two-role fixtures and separate compatibility fixtures
- [x] 4.6 Add component tests proving only two role labels render and candidate audio never triggers an answer

## 5. Authoritative Answer Cancellation

- [x] 5.1 Add a replaceable answer-task coordinator with conditional final-state transitions and adapter-level abort support
- [x] 5.2 Accept cancellation only for the authenticated user, matching interview and active answer-task revision
- [x] 5.3 Make repeated cancel commands return the same result without duplicate events or resource release
- [x] 5.4 Reject or isolate provider chunks and completion callbacks that arrive after accepted cancellation
- [x] 5.5 Resolve completion-versus-cancellation races with one server-authoritative final state
- [x] 5.6 Release points reservations exactly once for successfully cancelled tasks and preserve normal settlement when completion wins
- [x] 5.7 Record zero-cost cancellation usage for active-pass users without consuming another entitlement
- [x] 5.8 Exclude cancelled partial output from usable-answer history, review advice and successful AI quality metrics
- [x] 5.9 Add API tests for authorization, idempotency, late chunks, race outcomes, retry, reservation release and unlimited-pass cancellation

## 6. Answer Workspace Stop Control

- [x] 6.1 Track the current active answer task independently from the historical answer page being viewed
- [x] 6.2 Add a compact, keyboard-accessible “终止回答” control for queued and generating tasks
- [x] 6.3 Add a non-duplicating cancelling state and synchronize the authoritative result across authorized Web clients
- [x] 6.4 Display “回答已终止” without presenting partial text as complete or evidence-backed advice
- [x] 6.5 Keep audio capture, transcript, draft, screenshot task, answer pagination and future question triggers unchanged after cancellation
- [x] 6.6 Allow explicit re-answering to create a new task while preserving the previous cancelled task state
- [x] 6.7 Add component tests for latest generation, historical-page viewing, repeated clicks, cancellation failure, completion race and re-answer
- [x] 6.8 Add phone, tablet and desktop interaction checks for reachability, touch target, focus state and no confusion with ending the interview

## 7. Interview Start Wording and Session State

- [x] 7.1 Replace the desktop companion primary “开始收音” label with “开始面试” and update ready-state supporting copy
- [x] 7.2 Route Web and desktop start actions through one idempotent session-start command and synchronize the resulting live/capturing state
- [x] 7.3 Keep manual-mode start free from microphone or system-audio activation
- [x] 7.4 Keep audio-mode start blocked until each selected source has permission and a valid readiness check
- [x] 7.5 Preserve visible capture, pause, resume, stop, reconnect and error controls after the wording change
- [x] 7.6 Add desktop and Web tests for ready, missing-permission, manual, already-started and restarted-client states

## 8. AI Evaluation, Privacy and Verification

- [x] 8.1 Extend `ai/evals/` with synthetic two-channel cases for interviewer questions, candidate false triggers, echo, overlap, incomplete questions and source degradation
- [x] 8.2 Add answer-cancellation evaluation cases proving cancelled partial text is not treated as a successful recommendation
- [x] 8.3 Verify logs, fixtures and metrics exclude raw audio, full sensitive transcripts and cross-session speaker identity
- [x] 8.4 Run protocol, API, desktop and Web tests plus workspace typechecks and production builds
- [x] 8.5 Run browser interaction review for two-role transcripts, source degradation, answer termination, history paging and responsive layouts
- [x] 8.6 Check Markdown links and run strict validation for this change and every reconciled active change
- [x] 8.7 Review each capability scenario against implementation and record any intentionally deferred provider-level abort limitation
