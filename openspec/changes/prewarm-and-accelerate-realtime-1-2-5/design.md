## Context

The 1.2.4 client keeps microphone and system-audio monitors open while a bound session is preparing, but its React lifecycle stops those monitor streams when the session turns live. `DesktopRealtimePublisher.start()` then creates authorization/transport and opens both devices again. Backend ASR prewarm is currently scheduled only at live start or publisher attachment. Physical 1.2.4 evidence shows no transport backlog, reconnect, retransmission, or sequence gap, so the remaining start delay is primarily orchestration cold start and the remaining stop delay is endpoint tail plus provider finalization/rendering.

The local acceptance app continues to use production public endpoints. Backend/Web changes are therefore validated locally and by tests but are not considered physically accepted until a separately authorized production deployment. Preparation audio is sensitive and must remain local; readiness must not start billing or transcription.

## Goals / Non-Goals

**Goals:**

- Reuse the already-authorized preparation media streams when a bound session becomes live.
- Schedule provider warmup when a preparing session is bound, refresh stale warmup best-effort, and never block interview start on warmup.
- Reduce system-audio terminal latency without making microphone pauses unnaturally aggressive.
- Keep provisional text visible and bound a committing state even if the provider final event is late.
- Record enough timestamps to locate latency across desktop, backend/provider, and Web render stages.
- Preserve one media owner, source-specific recovery, existing UI layout, identity, endpoints, and protocol compatibility.

**Non-Goals:**

- Uploading or transcribing preparation audio.
- Creating a billable live publisher before the authoritative session start.
- Changing answer prompts, model selection, billing rules, persistence, or production deployment.
- Claiming Intel macOS or Windows physical acceptance from an Apple Silicon test.

## Decisions

### Transfer warmed media ownership instead of reopening devices

`LocalSourceMonitor` will expose a one-shot transfer that detaches its diagnostic processors while retaining its open `MediaStream` handles. The live publisher receives those sources and builds its production AudioWorklet/segmenter over them. The transfer is generation-scoped and consumed once; failure closes the transferred source and falls back to the existing source-specific open/recovery path.

Alternative considered: keep both monitor and publisher captures alive. Rejected because it creates duplicate system capture ownership, excess callbacks, and route-switch ambiguity. Alternative: merely shorten binding polling. Rejected because it does not remove device reopen latency.

### Keep publisher authorization live-only

Preparation binding schedules provider warmup and exposes readiness, but the desktop does not upload audio and does not create the billable live publisher until session status is authoritative `live`. This keeps privacy and billing enforcement server-side. Warmup is best-effort, has a bounded freshness window, and is refreshed when necessary; start never waits for it.

Alternative considered: open the production publisher WebSocket during preparation. Rejected for this patch because it expands the authorization protocol and makes accidental pre-live audio acceptance a higher-risk failure mode.

### Use source-aware adaptive terminal tails

System audio uses a 350 ms baseline silence tail, with peak-relative meaningful-speech release retained for residual program noise. Microphone retains a 480 ms baseline to preserve natural candidate pauses. Both retain the maximum-turn bound and terminal-priority transport behavior. Tests cover short pauses, consecutive turns, residual noise, and exact one-terminal emission.

Alternative considered: 100–200 ms tails for both sources. Rejected because it fragments ordinary speech and can trigger answers during thinking pauses.

### Separate provisional visibility from authoritative finality

Partial text remains the visible active block throughout `tail` and `committing`. A bounded finalization watchdog may label the active block incomplete, but it cannot erase it or prevent a newer segment from rendering. A late authoritative final may monotonically revise only its own segment generation.

Alternative considered: hide partial text until final. Rejected because it converts provider latency into visible product latency.

### Measure stage boundaries without content

Diagnostics carry timestamps/counters/reason codes only: preparation-ready, live-observed, publisher-connected, source-promoted/opened, first-frame, ACK, last-meaningful-speech, terminal, provider partial/final, and Web state/render. Raw PCM and transcript text are excluded.

## Risks / Trade-offs

- [Transferred tracks can end between preparation and live start] → Validate track state at consumption and fall back independently per source.
- [React cleanup ordering can leak a transferred stream] → Use a one-shot handoff holder with explicit expiry/close semantics and regression-test cleanup paths.
- [Provider warm sockets can expire before start] → Treat readiness as best-effort, refresh by age, and keep first real frame authoritative.
- [A 350 ms system tail can split slow speakers] → Keep microphone more conservative, retain overlap/revision semantics, and test natural pauses.
- [A bounded incomplete state can later receive final] → Require generation/segment monotonicity so late events cannot overwrite newer content.
- [Local app points at production] → Report desktop-only physical evidence separately from backend/Web test evidence and require authorization before deployment.

## Migration Plan

1. Add transfer ownership and endpointing regressions, then implement desktop handoff.
2. Add preparing-session prewarm readiness and provider finalization regressions, then implement backend changes.
3. Add Web continuity/timeout regressions without changing layout.
4. Run focused and full workspace verification plus strict OpenSpec validation.
5. Build/sign/install macOS arm64 1.2.5 alongside recoverable 1.2.4 rollback artifacts and launch it for local acceptance.

Rollback restores the 1.2.4 app. Backend/Web deployment is explicitly out of scope for this local acceptance step and requires separate approval.

## Open Questions

None. The user approved the combined warm-readiness, adaptive-terminalization, provisional-visibility, recovery, and diagnostics scope for 1.2.5.
