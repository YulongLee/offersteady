# Verification Record

## Dual-channel interview role routing

- Protocol and API tests verify microphone/headset routes to `candidate`, system audio routes to `interviewer`, multiple remote speaker IDs retain one display role, and legacy `unknown` or mixed-source events degrade without entering the transcript list.
- Service tests verify candidate speech, cross-channel echo, overlap, incomplete text, source loss and reconnect do not create unsafe duplicate triggers.
- Web component tests and browser review verify the transcript displays only “我/面试官”, exposes no role confidence or correction controls, preserves transcript revisions, and keeps manual input available during source degradation.
- Session cleanup removes temporary transcript candidates and confirmation evidence; the privacy review found no raw audio or cross-session speaker identity in fixtures, metrics or ordinary logging.

## Interruptible answer generation

- Protocol tests verify monotonic answer states and terminal `cancelled` behavior.
- API tests cover ownership, interview scope, revision conflicts, repeated idempotency keys, provider late chunks, completion/cancellation races, point reservation release and active-pass cancellation.
- Web tests cover stopping the latest answer, stopping while reading history, cancellation failure, re-answering, capture independence and removal of incomplete advice from the usable answer presentation.
- Browser review verifies the compact control is reachable, clearly named “终止回答”, disappears after cancellation, leaves interview controls intact and does not expose partial content as complete advice.

## Interview start wording

- Desktop tests verify the ready-state primary action is “开始面试”, while permission-required state cannot start and active states retain precise pause/resume wording.
- API and Web tests verify idempotent session start, dual permission gating, automatic capture only for ready dual-channel mode, and manual-mode start without audio activation.

## Responsive and accessibility review

- Browser interaction review passed at 390 px phone, 820 px tablet, 1200 px and 1440 px desktop, 200% zoom simulation and narrow landscape.
- All reviewed widths preserve two roles, avoid horizontal overflow and keep the existing conversation/answer layout and accessible divider behavior.
- Keyboard and touch checks cover answer termination, manual input, answer and screenshot actions.

## Intentionally deferred limitation

- Provider-level abort is best effort because a model supplier may not support immediate computation cancellation. The server-authoritative task still becomes `cancelled`, rejects late chunks, releases OfferSteady usage reservation exactly once and excludes partial text from successful advice and quality metrics.
- Mixed-audio automatic role inference remains outside the approved first-release scope. It degrades to manual input and requires a future OpenSpec change before implementation.
