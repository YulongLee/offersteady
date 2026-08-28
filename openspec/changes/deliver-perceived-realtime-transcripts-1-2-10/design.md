## Context

The current architecture already publishes 100-millisecond desktop audio revisions into persistent, source-specific DashScope realtime sessions. Provider receive pumps publish partial revisions directly to Redis/SSE, and the Web renders the newest revision without a reveal animation. Acceptance evidence nevertheless shows two bottlenecks: system output usually remains active until the eight-second safety boundary because residual program energy satisfies RMS continuation, and the Web derives an `incomplete` presentation from the age of the last partial while provider finalization is still within its normal budget.

## Goals / Non-Goals

**Goals:**

- Preserve continuous incremental audio and publish every new provider partial on the independent receive path.
- Release system-output speech promptly when voice-like temporal variation ends, without losing quiet speech or splitting ordinary short pauses.
- Make terminal admission immediately end the visible active state while provider final reconciliation remains authoritative and asynchronous.
- Establish content-free acceptance evidence and reopen a local 1.2.10 Apple Silicon companion for physical testing.

**Non-Goals:**

- Adding an on-device transcription model or replacing DashScope.
- Changing layouts, icons, permissions, prompts, billing, storage, or production deployment in this local acceptance cycle.
- Treating music classification as a general audio-understanding problem.

## Decisions

### Extend the current segmenter with temporal voice-release evidence

The segmenter will retain adaptive source thresholds and pre-speech audio, but system-output continuation will no longer refresh meaningful speech indefinitely from one above-threshold RMS sample. It will track a bounded rolling envelope and require recent variation or sustained high-confidence speech to refresh meaningful speech. Once voice-like variation disappears, the current short system tail closes the segment even if low residual energy remains. Microphone behavior remains conservative because its previous acceptance produced 39 of 40 silence terminals.

Alternative: lower the system silence duration or maximum turn. Rejected because it shortens every pause without distinguishing speech from residual program energy and risks fragmented questions.

Alternative: add a native WebRTC VAD dependency immediately. Rejected for this cycle because it expands native packaging risk across three platforms; deterministic temporal voice evidence can correct the observed release failure while leaving a replaceable VAD seam.

### Keep provider partial receipt independent of append and final work

Incremental desktop frames remain bounded at 100 milliseconds. The provider receiver remains the only owner of transcript event arrival and invokes the partial listener once per unseen provider revision. Backend persistence/metrics/question detection remain downstream and MUST NOT gate the transcript SSE event. Tests will prove multiple revisions can arrive and render before terminal commit.

Alternative: wait briefly on every audio append for a partial. Rejected because synchronous provider waits serialize audio publication and turn network jitter into capture backpressure.

### Separate visible terminal admission from authoritative final state

On `transcript-committing`, the Web freezes the latest partial and immediately presents it as no longer actively transcribing. It will not infer `incomplete` from client time. A later Backend `final` may reconcile text, while only an explicit Backend `incomplete` terminal may show incomplete. The Backend retains its bounded provider-final watchdog and source isolation.

Alternative: mark the partial as authoritative final at terminal ACK. Rejected because it would erase the distinction between a provider final and a recoverable partial.

### Version and local acceptance remain isolated

The companion version becomes 1.2.10 without layout, icon, identity, endpoint, signing, or permission changes. Automated checks precede an isolated local Backend/Web/companion launch. Production remains untouched until the user accepts the local behavior.

## Risks / Trade-offs

- [Temporal energy variation can still confuse music with speech] → Keep admission conservative, bound turns, expose content-free release evidence, and validate speech plus residual/music-like fixtures.
- [A short system pause may split one question] → Preserve a 350-millisecond tail and merge only through the existing monotonic segment path; validate short-pause continuity.
- [DashScope may withhold trailing words until commit] → Prompt local commit quickly and freeze the newest partial; final reconciliation remains background and bounded.
- [A reconnect during committing can leave only a partial] → Backend remains authoritative for explicit incomplete recovery and isolates the affected source generation.
- [Cross-platform envelope levels differ] → Use source-relative rolling features and deterministic tests; do not claim physical acceptance on untested hardware.

## Migration Plan

1. Add Desktop regressions for residual system energy release, ordinary pause continuity, quiet speech, and bounded partial cadence.
2. Implement temporal release evidence and 1.2.10 metadata without changing capture ownership or permissions.
3. Add Backend regression for independent multi-revision partial publication and terminal admission.
4. Fix Web committing/incomplete presentation and add regressions.
5. Run full relevant tests, typechecks, builds, and strict OpenSpec validation.
6. Build and open an isolated Apple Silicon 1.2.10 local acceptance chain; leave production unchanged.
7. After explicit user approval, build and verify versioned production artifacts, retain Backend/Web rollback images, upload artifacts before changing the manifest, switch Backend/Web without recreating PostgreSQL or Redis, and run public smoke checks.

## Open Questions

Physical acceptance will determine whether DashScope's provider partial cadence alone meets the sub-800-millisecond visible target or whether a later provider comparison/on-device draft layer is required.
