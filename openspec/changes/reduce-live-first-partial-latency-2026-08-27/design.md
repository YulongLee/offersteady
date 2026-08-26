## Context

The 2026-08-27 live sample showed stable Desktop delivery (zero resend, zero reconnect, queues at 0–1), Backend ingress p50 near 3 ms, and Browser render p50 near 5 ms. The first visible partial remained 4.7 seconds at p50. Qwen sessions are already reusable and prewarm is enabled, but both channel prewarms contend on one global gateway lock while opening external WebSockets. The live-start API returns before either future is actually ready, so speech arriving immediately can block behind cold connection creation. The existing “prewarm ready” callback also means connection construction completed, not that both channel futures finished before capture begins.

## Goals / Non-Goals

**Goals:**

- Open microphone and system provider sessions concurrently and safely.
- Give live-session start a bounded readiness gate so immediate speech normally reaches an already-open provider connection.
- Keep first audio emission bounded and incremental; preserve manual finalization accuracy.
- Measure provider-ready, first-audio-append, first provider partial, first delivered event, and first browser paint per utterance without content.
- Meet a synthetic warm-path first-append p95 below 250 ms and target production speech-start-to-first-visible p50 below 1.5 seconds, p95 below 3 seconds when the input contains recognizable speech.

**Non-Goals:**

- No model migration, Server VAD switch, fabricated placeholder text, raw-audio persistence, Redis/SSE replacement, or answer-prompt change.
- Music-only input is not treated as a contractual speech-recognition sample.
- The optimization does not guarantee external provider latency during a regional outage.

## Decisions

### Use per-session-channel creation locks

Provider WebSocket I/O will occur under a lock scoped to `session_id + source_kind`, not the global session-map lock. The global lock remains only for short map operations. This lets microphone and system prewarm in parallel while preventing duplicate connections for the same channel. Opening all connections without a key lock was rejected because two concurrent first frames could leak sockets and split transcript state.

### Bound live-start readiness instead of blocking indefinitely

`start_live_session` will launch both prewarms and wait for them concurrently up to a small configurable deadline. Success means both provider sessions exist and are ready before the API returns; timeout or provider failure is recorded and capture continues through the existing lazy fallback. An unbounded wait was rejected because an external ASR incident must not make the interview-start API hang.

### Preserve real partials and existing endpointing

The Desktop continues to emit initial buffered speech promptly and subsequent payloads every 100 ms. We will test the first payload boundary but will not display invented text or commit an utterance early. Lowering silence windows or switching turn detection was rejected because those change final completeness rather than first-partial delivery.

### Separate readiness and first-visible telemetry

Each channel records prewarm scheduled/ready/failed/timeout counts and duration. First-visible metrics are keyed by session, channel, and utterance and only the earliest provider partial/event/browser paint contributes. This avoids treating later revisions or music-triggered VAD age as a stage latency.

## Risks / Trade-offs

- [Two provider connections consume quota before speech] → Limit to active interviews, preserve idle/session cleanup, and fall back without retries on bounded start timeout.
- [Start page waits briefly] → Cap the gate and expose truthful “preparing realtime speech” state; the delay happens before users can lose their first sentence.
- [Connection races leak sockets] → Serialize creation per session-channel and close any losing candidate before map replacement.
- [Provider or network p95 remains high] → Report it separately from Desktop, Backend, and Browser stages instead of masking it with aggregate timing.

## Migration Plan

1. Add deterministic concurrent-prewarm, timeout/fallback, first-frame, and first-visible telemetry regressions.
2. Deploy the backward-compatible Backend first; Desktop protocol 2.0 and package 1.1.7 remain unchanged.
3. Verify health, ASR connection counts, zero queue growth, and a live recognizable-speech sample on both channels.
4. Roll back the Backend image if connection counts exceed two per active interview, live-start errors rise, or the bounded gate fails open incorrectly.

## Open Questions

None. The user authorized implementation and production optimization after the live 1.1.7 acceptance sample.
