## Context

The packaged Electron companion captures microphone and display-loopback audio continuously and emits an interim snapshot every 100 ms. A client-side energy segmenter currently finalizes microphone speech after only 220 ms below threshold and assigns the next audio a new segment ID. Normal Mandarin breathing and thinking pauses therefore become separate final transcripts. The Web only collapses duplicate/containing records, so adjacent fragments remain separate cards. Backend ASR sessions can stream revisions for a stable segment ID, but the user-visible behavior is dominated by the premature client boundary.

The change crosses the packaged desktop, realtime backend, and Web workspace. Raw PCM must remain memory-only, protocol compatibility must be preserved, and automatic interviewer answers must continue to depend only on trusted system audio.

## Goals / Non-Goals

**Goals:**

- Show continuous speech as one transcript card whose text grows through interim revisions and becomes final only at a meaningful pause.
- Preserve low-latency audio upload and ASR partial output while tolerating normal speech pauses.
- Bound segment size and memory use during uninterrupted speech.
- Safely join residual adjacent same-role fragments for display and interviewer-turn question context.
- Ship compatible companion binaries and deploy affected Web/Backend services with rollback artifacts.

**Non-Goals:**

- Do not persist raw audio or enable transcript persistence by default.
- Do not add biometric speaker identification or infer real identities.
- Do not replace the configured ASR provider or introduce a client-side model.
- Do not merge speech across a role change, a long silence, an overlap/conflict marker, or a session boundary.
- Do not redesign the live workspace outside transcript continuity feedback.

## Decisions

### 1. Keep client-side segmentation but use source-specific speech hangover

The desktop will keep one segment ID through a bounded pause, publish interim snapshots at the existing cadence, and finalize microphone speech after approximately 1.1 seconds of silence. System audio uses a shorter approximately 0.8 second boundary so interviewer questions remain responsive. A hard maximum segment duration finalizes very long uninterrupted turns.

This preserves provider independence and bounded memory. Relying only on provider VAD was rejected because production uses manual turn detection for lower and more predictable final latency. Keeping the existing 220 ms threshold was rejected because it is shorter than normal phrase pauses.

### 2. Treat interim snapshots as revisions, not separate utterances

All snapshots before finalization retain the same `segmentId` and monotonically increase `revision`. The backend continues to upsert by `(sessionId, segmentId)` and publishes only non-empty ASR revisions. Finalization commits the same segment and does not create an additional transcript identity.

A new protocol version is unnecessary because the existing fields already express this behavior.

### 3. Add a pure Web conversation-turn projection

The Web will first reconcile revisions by ID, then project residual adjacent same-role fragments into one display turn when they are close in time and safe to join. The projection retains all contributing source segment IDs so pending-question controls still attach correctly. It never changes authoritative stored transcripts.

Only increasing the desktop silence threshold was considered, but older installed companions and provider-side early boundaries can still produce fragments. A display projection provides backward-compatible mitigation while new binaries roll out.

### 4. Use the same safe turn projection for automatic-question text

The latest eligible interviewer question text will be assembled from consecutive final system-audio fragments after the candidate's latest final turn. Automatic triggering remains tied to a final trusted system segment and existing confidence gates; the assembled text supplies context without allowing microphone speech to trigger an answer.

Adding a separate question-normalization model call was rejected because it adds latency and another failure point. The existing quick-answer normalization remains responsible for punctuation and references.

### 5. Verify with synthetic time-series audio and transcript fixtures

Desktop tests will simulate speech, short pauses, long pauses, maximum duration, and separate microphone/system thresholds. Web tests will cover revision replacement, safe joining, role changes, long gaps, and pending source IDs. Backend tests will verify stable upserts and complete interviewer context without recording real transcript content.

## Risks / Trade-offs

- [Longer finalization delays the `已确认` label and automatic question trigger] → Continue interim output every 100 ms and keep the system-audio boundary shorter than the microphone boundary.
- [Background noise can keep a segment open] → Retain start/continue hysteresis and enforce a hard maximum segment duration.
- [Web joining can combine two genuinely separate sentences] → Restrict joining to the same role, a short gap, no overlap, and bounded total duration; retain punctuation between fragments.
- [Older companions remain fragmented] → Web projection improves display immediately, while release metadata directs users to the new binary for correct ASR context.
- [Changing desktop binaries can affect capture stability] → Reuse the existing capture owner and transport, add segmenter regressions, and do not change permission or source-recovery code.

## Migration Plan

1. Add tests and compatible Web/Backend behavior first.
2. Build and verify desktop packages for supported platforms, then publish a versioned release and update the release manifest.
3. Deploy Backend and Web only after local regressions pass; do not restart PostgreSQL, Redis, admin, or analytics services.
4. Verify health, realtime connection, interim/final transcript events, and download metadata.
5. Roll back Web/Backend images and the release manifest independently if needed; existing protocol messages remain compatible.

## Open Questions

None. Initial thresholds are treated as measured product defaults and can be tuned through follow-up synthetic and consented acceptance runs.
