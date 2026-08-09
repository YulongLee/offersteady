# Verification Record

## Dual-channel interview role routing

- Protocol and API tests verify microphone/headset routes to `candidate`, system audio routes to `interviewer`, multiple remote speaker IDs retain one display role, and legacy `unknown` or mixed-source events degrade without entering the transcript list.
- Service tests verify candidate speech, cross-channel echo, overlap, incomplete text, source loss and reconnect do not create unsafe duplicate triggers.
- Web component tests and browser review verify the transcript displays only “我/面试官”, exposes no role confidence or correction controls, preserves transcript revisions, and keeps manual input available during source degradation.
- Session cleanup removes temporary transcript candidates and confirmation evidence; the privacy review found no raw audio or cross-session speaker identity in fixtures, metrics or ordinary logging.
- Production regression evidence showed the same interviewer utterance arriving on `system/interviewer` and `microphone/candidate` with 92.6–100% text similarity in overlapping windows. The hotfix explicitly requests echo cancellation for the default microphone and suppresses the later cross-channel duplicate before it becomes a visible transcript or question trigger. Targeted backend tests, the full 61-test foundation suite, all 44 desktop tests, desktop typecheck and strict OpenSpec validation passed.
- User 3006's privacy-safe production diagnostics showed desktop `0.1.3` system audio emitting only from 21:35:45 to 21:37:50 while the microphone continued until 21:58:38; 235/238 system-health samples remained `track-live/silent`, with no ASR, transport or non-filter degradation error. Desktop `0.1.4` now detects ended/muted tracks, non-running AudioContext, stalled processing callbacks and a previously active system signal that becomes persistently silent. It rebuilds only system audio with bounded backoff and uses a 480 ms system-only finalize window for meeting-software pauses. All 49 desktop tests, desktop typecheck, production build, diff check and strict OpenSpec validation passed.

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
