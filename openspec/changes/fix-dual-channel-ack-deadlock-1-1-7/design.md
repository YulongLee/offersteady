## Context

Companion 1.1.6 multiplexes microphone and system audio over one WebSocket with an eight-frame in-flight window per channel. Production metadata from session `session-39090045e3974f06bc7e770ff40f3280` showed capture callbacks continuing near 23 Hz while microphone unique frames stopped at 16/ACK 15 and system unique frames stopped at 83/ACK 52. The microphone later sent a fresh 0–7 window while diagnostics still retained the earlier ACK 14; neither channel made subsequent forward progress and queues grew without a reconnect.

The current recovery gate is transport-wide: the first ACK from either channel resolves replacement recovery. At the same time, `RealtimeReliabilityController.evaluate` deliberately ignores a source already marked `RECOVERING`. That combination can strand the other channel in `RECOVERING` forever. The transport also treats every close code 1000 as intentional, although only a local `stop()` flag proves intent, and its send-window/ACK diagnostics are cumulative across transport generations, obscuring the failure.

Raw audio remains memory-only. Regression fixtures and production diagnostics contain only generated PCM or metadata.

## Goals / Non-Goals

**Goals:**

- Guarantee bounded recovery when either active channel fills its send window without forward ACK progress.
- Require every channel that produced media on a replacement transport to receive a fresh ACK before that channel becomes healthy.
- Keep silence valid: a channel that produced no replacement media remains ready/idle without consuming recovery attempts.
- Distinguish intentional transport shutdown from every unexpected close code and reconnect unexpected closures.
- Atomically align channel sequences and discard stale buffered envelopes at publisher-generation boundaries.
- Preserve the unaffected capture source across device-only changes and preserve monotonic terminal ordering.
- Make production diagnostics sufficient to identify generation, channel progress, window saturation, and recovery outcome without content.

**Non-Goals:**

- No DashScope model, prompt, answer, billing, Web transcript semantics, or persistence changes.
- No replay of audio older than the bounded in-memory recovery window.
- No protocol 3.0 migration or raw-audio logging.
- No claim that physical Bluetooth hardware will always reconnect when macOS exposes no usable device.

## Decisions

### Track forward progress per channel and transport generation

Each transport generation owns per-channel sent and acknowledged high-water marks. A sent frame starts or preserves the oldest-unacknowledged deadline; additional sends cannot move that deadline forward. ACK handling is monotonic and only clears frames in the matching generation/channel. Cumulative counters remain available, but operational watchdog state uses generation-local values.

Using only queue depth was rejected because a queue can be non-empty during healthy throughput. Using the latest send timestamp was rejected because continuous speech indefinitely postpones the timeout.

### Make replacement readiness channel-aware

Replacement connection-state proves only control-plane readiness. Each enabled channel transitions independently: silent channels remain `STARTING/idle`, channels that produce media enter a bounded `RECOVERING` ACK wait, and only a fresh ACK for that channel returns it to `HEALTHY`. One channel's ACK cannot clear the other channel's pending/recovering state. A shared transport replacement attempt succeeds once the transport is ready and every channel that has produced media has either ACKed or remains within its bounded deadline.

Maintaining one global first-ACK promise was rejected because it reproduced the production deadlock.

### Treat close intent explicitly

`stop()` records an intentional-close generation before closing the socket. `onclose` suppresses recovery only for that exact intentional closure or after the publisher is stopped/replaced. An unexpected code 1000 is treated like any other recoverable network loss. Stale socket events are ignored through socket identity/generation checks.

Treating code 1000 itself as intentional was rejected because proxies, servers, and lifecycle races can produce clean closes without a user stop.

### Use one bounded deadlock circuit breaker

The transport exposes channel progress snapshots. The watchdog replaces the shared transport when an active channel has an unchanged oldest-unacknowledged frame beyond the lost-ACK deadline or when a saturated eight-frame window shows no ACK progress. Recovery is single-flight and attempt-bounded. A source marked `RECOVERING` is still evaluated for its fresh-media ACK deadline; it is not exempt forever.

Unbounded retransmission and higher queue limits were rejected because they increase latency and traffic without restoring ordering.

### Reconcile replacement state before accepting new media

On replacement, capture writers pause, old transport and per-generation in-flight markers are retired, authoritative resume offsets are received, sequencers are aligned, stale queued frames at or below offsets are discarded, and only then are sources resumed. Bounded replay is allowed only for frames whose sequence is strictly greater than the authoritative offset and contiguous from `offset + 1`; otherwise the old buffer is discarded and capture resumes from the authoritative next sequence.

### Release as companion 1.1.7 with a production soak gate

Tests will reproduce the exact production shape: one channel ACKs the replacement while the other stalls, both windows later saturate, capture callbacks continue, and an unexpected clean close occurs. Packaging covers macOS arm64/x64 and Windows x64. Publication requires focused tests, full desktop tests/typecheck/build, Backend compatibility tests, strict OpenSpec validation, artifact checksums/signing checks, and a metadata-only live soak.

## Risks / Trade-offs

- [Replacing a shared transport interrupts the healthy channel briefly] → Keep recovery single-flight, resume from authoritative offsets, and bound the interruption instead of allowing silent permanent loss.
- [A slow but alive network triggers replacement] → Use oldest-unacknowledged age plus unchanged ACK high-water mark, not transient latency alone.
- [Old socket ACK arrives during replacement] → Gate all events by transport/socket generation before mutating buffers or health.
- [Silent microphone never proves media health] → Report ready/idle truthfully and start the ACK deadline only when that channel produces media.
- [Discarding non-contiguous buffered PCM can lose a short fragment] → Prefer bounded, explicit loss and a new sequence boundary over replay storms or duplicated transcripts.
- [Cross-platform device semantics differ] → Keep transport logic platform-neutral and run Windows packaging/tests; physical macOS headset switching remains an additional acceptance case.

## Migration Plan

1. Add deterministic transport, reliability, publisher, and lifecycle regressions before changing runtime behavior.
2. Implement generation-aware close handling, per-channel progress, channel-aware recovery gates, and atomic resume reconciliation.
3. Run focused and full Desktop/Backend verification plus a long-running synthetic dual-channel soak.
4. Increment to 1.1.7, build and verify all supported artifacts, and preserve 1.1.6 manifests for rollback.
5. Publish compatible server changes first only if tests require them, then publish signed companion artifacts and manifest last.
6. Run a metadata-only production test with speech on both channels and one headset remove/reconnect cycle.

Rollback restores the immutable 1.1.6 manifest and prior application package. Compatible additive diagnostics can remain deployed.

## Open Questions

None. The observed counters define the missing acceptance case and the user has authorized implementation, self-test, and production rollout.
