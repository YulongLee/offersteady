## Context

Release 1.2.10 already streams provider partials on an independent receive path and freezes a visible partial at terminal admission. Physical acceptance nevertheless shows that DashScope can withhold trailing words until a later partial or `completed` event. OfferSteady cannot manufacture unavailable text, but it can shorten local release, ensure the last PCM append and commit reach the provider without application queue delay, and deliver every post-commit revision immediately.

The current desktop emits 100 ms incremental PCM snapshots and uses 480 ms microphone / 350 ms system-output silence windows. Backend admits terminal frames into a bounded source queue, sends `input_audio_buffer.commit` only after all earlier audio for that source, waits at most two seconds for provider completion, and does not retry a missing terminal completion. Web applies monotonic segment revisions and keeps provider final authoritative. Audio and transcript contents remain excluded from diagnostics.

## Goals / Non-Goals

**Goals:**

- Reduce clear-silence endpoint delay without splitting normal pauses or quiet trailing speech.
- Bound terminal queue wait and preserve exact last-audio-before-commit ordering under load.
- Allow post-commit provider partials to update the visible text before `completed`.
- Attribute tail delay across desktop release, terminal queueing, provider commit/final, event delivery, and browser paint using content-free evidence.
- Ship the same behavior as companion 1.2.11 on Apple Silicon, Intel macOS, and Windows while preserving the approved product surface.

**Non-Goals:**

- Replacing or supplementing DashScope, enabling Server VAD in production, or guaranteeing unavailable provider words at speech stop.
- Changing UI layout, application permissions, identity, icons, prompts, billing, answer generation, or persistence policy.
- Lowering the provider-final timeout merely to hide latency.

## Decisions

### Use a bounded adaptive release window inside the existing segmenter

The desktop will derive a release duration from the current source noise floor, turn peak, recent temporal activity, and distance from the continuation threshold. Clear silence after strong speech uses a shorter floor; ambiguous residual energy retains the current conservative ceiling. A resumed voice-like signal before the chosen deadline keeps the same segment. The existing maximum meaningful release and maximum turn remain safety boundaries.

Alternative: set both tails to a fixed 200 ms. Rejected because English endings, quiet syllables, and ordinary hesitation would fragment more often across microphones and operating systems.

Alternative: add native WebRTC VAD. Rejected because this change must not add cross-platform native packaging risk and current envelope evidence already provides a replaceable VAD seam.

### Prioritize terminal admission without overtaking earlier source audio

Each source retains ordered ownership. When a worker drains a batch, it coalesces all same-segment PCM preceding a terminal into the terminal job and processes that terminal before unrelated later partial jobs. A saturated queue may replace only a partial with a terminal, preserving displaced same-segment PCM as today. Terminal queue wait is recorded and bounded; cold-path persistence, metrics aggregation, and question detection remain outside commit admission.

Alternative: use an unconstrained global priority queue. Rejected because a terminal must never overtake unsent PCM for its own segment and global priority would weaken per-source isolation.

### Keep provider commit manual and accept post-commit partials until completed

Manual commit remains the production mode because the existing Server VAD probe did not reliably finalize in its observation window. The receive pump continues accepting unseen non-empty `text` events after commit and publishes them immediately. Only `completed` freezes the provider utterance. A short zero-PCM suffix is implemented only behind a disabled-by-default flag and evaluated with synthetic content and real-provider timing before any production enablement.

Alternative: shorten the two-second final timeout. Rejected because it converts late but complete results into incomplete results without making trailing words arrive earlier.

### Preserve monotonic presentation while allowing authoritative correction

Web keeps the longest visible non-final hypothesis when a provider partial retracts, immediately accepts equal-or-longer post-commit revisions, and accepts provider final as authoritative even when it is shorter or corrected. A post-commit partial cannot reactivate the caret, and any partial after final is rejected by lifecycle precedence.

### Measure stages without retaining content

Diagnostics will carry timestamps, revisions, source kind, text lengths, and final-added-character counts only. Acceptance distinguishes `speech end -> terminal`, `terminal -> commit`, `commit -> last partial`, `commit -> final`, and `final -> browser paint`. No raw PCM or transcript content is logged or persisted.

## Risks / Trade-offs

- [Short adaptive release clips quiet final syllables] → Keep the current ceiling, require clear noise-relative evidence for the short floor, retain pre-speech/tail PCM, and add quiet-ending fixtures.
- [Terminal priority overtakes required audio] → Preserve per-source order and merge preceding same-segment PCM into the terminal before commit.
- [A synthetic silence suffix increases latency or accuracy errors] → Default it off and enable only after an isolated measured win with no regression.
- [DashScope still withholds trailing words until completed] → Continue immediate partial delivery, keep the two-second bounded final path, and report this provider-controlled remainder honestly.
- [Thresholds behave differently across platforms] → Use relative signal features, run deterministic cross-platform tests/builds, and do not claim unperformed physical acceptance.

## Migration Plan

1. Add failing desktop, backend, gateway, and Web regressions plus privacy-safe timing assertions.
2. Implement adaptive release and ordered terminal batching behind existing commercial endpointing behavior.
3. Implement the disabled short-silence experiment and post-commit provider regression coverage.
4. Increment to 1.2.11 and run relevant full tests, typechecks, production builds, and strict OpenSpec validation.
5. Open the local Apple Silicon companion against the unchanged online service for user acceptance; do not deploy or reconfigure production.
6. After explicit approval, retain rollback artifacts and deploy Backend, Web, then immutable cross-platform companion artifacts.

## Open Questions

- Physical acceptance will determine the final adaptive release floors and whether the disabled short-silence experiment merits a later production flag change.
