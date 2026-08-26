## Context

Desktop 1.1.2 uses a multiplexed binary WebSocket with a bounded in-flight window. When an ACK stall is detected, it stops the old transport, creates a new publisher, restarts capture and waits for the replacement transport to receive an audio ACK. Production system-audio evidence showed sequence 269 as the last ACK, three replacement publishers created at the ACK timeout cadence, and then one HTTP `/frames` request returning 422. The fallback request does not carry the publisher token required by `RealtimeFrameIngestRequest`; moreover production disables the legacy HTTP route, so that branch cannot be a valid recovery path.

The current recovery gate also conflates transport readiness with media forward progress. A valid replacement WebSocket can be discarded merely because the source is silent during the ACK deadline. After the retry budget is exhausted, capture callbacks continue while no upload path exists, leaving the session falsely reported as capturing. Separately, initial SSE bootstrap materializes full retained events even though the normal stream is cursor-based.

## Goals / Non-Goals

**Goals:**

- Keep one bounded replacement recovery active and prevent silence from creating publisher churn.
- Require real frame acknowledgement before reporting healthy delivery.
- Eliminate the unusable production HTTP fallback and expose terminal delivery failure truthfully.
- Keep fresh audio sequencing aligned with the publisher identity and server resume offsets.
- Return a minimal initial stream snapshot without full historical event materialization.
- Preserve immediate partial delivery and monotonic transcript revisions.
- Ship a verified desktop patch 1.1.3 on the existing protocol and bundle identity.

**Non-Goals:**

- No ASR provider/model, VAD threshold, RAG, answer, billing or transcript-content changes.
- No persistence of raw audio or transcript text in diagnostics.
- No realtime protocol version bump and no replay of unrecoverable PCM.
- No production deployment in the local joint-test step.

## Decisions

1. **Split WebSocket readiness from media health.** The Backend's existing initial `connection-state` is the authoritative transport-ready event. A replacement transport may remain established while silent; it is not recreated merely because no media was produced. The source remains `RECOVERING` until the first newly produced frame receives `frame-accepted` or `terminal-accepted`. Alternative: send synthetic silence to obtain an ACK. Rejected because it invents media and can affect usage and ASR state.
2. **Only apply an ACK deadline after a replacement has produced or queued media.** Recovery waits for a source-produced signal before starting the forward-progress deadline. If no speech occurs, the connection remains ready and idle. If media is produced and no ACK arrives, the bounded replacement budget advances. Alternative: keep the fixed deadline from connection open. Rejected because quiet interviews are normal.
3. **Use WebSocket-only production recovery.** Remove the automatic legacy HTTP branch from the desktop publisher. After bounded replacement failure, stop capture upload, set terminal `LOST`, clear bounded PCM and show a reconnect action. Alternative: repair HTTP per-frame fallback. Rejected because production disables it, it duplicates authentication/ordering behavior, and it is slower than re-establishing WebSocket v2.
4. **Make terminal failure sticky until an explicit restart/rebind.** Capture callbacks may remain observable for diagnostics, but product health and server status cannot return to capturing without a current publisher ACK. This prevents desired session state from masking missing delivery.
5. **Align sequence ownership to the authoritative connection boundary.** A replacement publisher waits for server `resumeOffsets` before capture restarts. A server that scopes receipts to the new Publisher returns `-1`, so sequencing starts at zero; a backward-compatible server that retains the session/source offset is resumed at offset plus one. Old pending frames and ACKs cannot enter the replacement gate. Deterministic tests cover both the earlier sequence 269 failure and the observed production boundary at sequence 3599.
6. **Bootstrap streams with current state, not retained history.** The first SSE event returns runtime, transcripts, candidates, cursor and only latest operational events required to render current state. Historical events remain available through existing APIs and subsequent cursor deltas. Alternative: retain all events in every initial snapshot. Rejected because it places retained history on the critical entry path.
7. **Coalesce only superseded revisions.** Backend/Web may collapse multiple queued revisions for the same segment to the newest revision in one scheduling turn, but MUST publish/render non-final partials and MUST NOT let an older revision overwrite a newer or final revision.
8. **Patch release sequencing.** Compatible Backend and Web behavior is verified first. Desktop version becomes 1.1.3, preserving protocol 2.0 and bundle identifier. Local installation precedes any signing/publication decision.

## Risks / Trade-offs

- [A silent replacement remains `RECOVERING` until speech occurs] → Show “连接已恢复，等待音频验证” and transition immediately on the first ACK; do not create more publishers.
- [Removing HTTP fallback leaves no second transport technology] → Prefer one fully verified WebSocket path and a truthful terminal failure over an untested false fallback; explicit restart/rebind remains available.
- [Minimal snapshots could omit an event used to reconstruct current UI] → Include latest stateful event kinds and keep transcripts/candidates/runtime authoritative; add refresh/re-entry regressions.
- [A sticky LOST state can interrupt an interview] → It reflects actual data loss, stops misleading operation, and provides a bounded explicit recovery action.
- [Patch changes desktop and server together] → Keep additions backward-compatible and deploy server support before any public desktop manifest update.

## Migration Plan

1. Add compatible Backend stream/bootstrap tests and any optional readiness metadata without changing protocol 2.0.
2. Implement desktop two-stage recovery, remove automatic legacy HTTP fallback and add exact production regressions.
3. Implement Web truthful state and minimal bootstrap regressions.
4. Run focused and full Backend/Web/Desktop suites, type checks, production builds and strict OpenSpec validation.
5. Bump/build local desktop 1.1.3, replace the local application using a recoverable backup, launch it and execute a controlled system-audio test.
6. A later production rollout deploys Backend/Web first, signs and publishes desktop artifacts second, and updates the manifest last. Rollback restores the prior manifest and compatible Backend remains safe for 1.1.2 clients.

## Open Questions

None for local implementation and joint testing.
