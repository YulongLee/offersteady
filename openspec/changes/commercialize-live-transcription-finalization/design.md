## Context

The current Electron companion captures microphone and system output separately, applies an RMS energy segmenter, emits interim snapshots about every 100 ms, and sends a final frame after a local silence boundary or a 30-second hard limit. The backend serializes each source through a bounded queue and keeps a persistent Qwen Realtime ASR connection in Manual turn-detection mode. The Web receives transcript revisions through the existing session SSE and projects adjacent segments into conversation turns.

This is a valid low-latency foundation, but three contracts are weak. First, system-output noise can continuously exceed the capped continuation threshold, so the desktop never emits the final frame. Second, final frames compete with obsolete partial frames in both desktop and backend queues and are not durably acknowledged as terminal work. Third, Web projection copies the newest joined segment's `isFinal`, allowing a new partial to make previously confirmed text appear active again. Provider VAD was previously measured as slower and incomplete for the current production fixture, so switching all traffic to `server_vad` is not a safe immediate fix.

The product requires explicit quick-answer and screenshot-answer controls. Transcription may identify and display interviewer speech, but it must never start a billable answer by itself. Raw audio must remain ephemeral.

## Goals / Non-Goals

**Goals:**

- End every detected utterance in a bounded, deterministic terminal state under normal silence, persistent background noise, provider timeout, reconnect, and queue pressure.
- Preserve low-latency partial text while making final state monotonic and role-correct.
- Ensure terminal audio work cannot be silently discarded behind obsolete interim work.
- Recover one unhealthy source without interrupting the other source or the interview session.
- Provide commercial SLO evidence, production-safe rollout controls, and per-layer rollback.
- Improve existing installations server-side while shipping the complete endpointing behavior in the next signed desktop release.

**Non-Goals:**

- Replace Qwen Realtime ASR or couple the application directly to one provider-specific API.
- Automatically invoke answer generation from speech, change answer ordering, or alter billing.
- Persist raw audio or transcript text in new operational telemetry.
- Rebuild the existing SSE transport, desktop capture runtime, or live page layout.

## Decisions

### 1. Introduce an explicit source-scoped turn state machine

Each microphone/system source follows `idle -> speaking -> tail -> committing -> final|incomplete`, keyed by a stable segment ID and monotonic revision. A segment may leave a terminal state only by creating a new segment ID. Source state includes last audio activity, last meaningful energy, last provider revision, finalization reason, and terminal acknowledgement.

This replaces loosely coupled booleans and timestamps. The alternative—only tuning silence constants—cannot guarantee recovery when noise, queue pressure, or a missing provider event is the cause.

### 2. Keep Manual provider turns as the production default and use hybrid endpoint evidence

The desktop remains the primary low-latency endpoint detector because the current real-provider benchmark showed Manual completion in under one second while provider VAD failed to complete within the configured window. Endpointing is upgraded from capped absolute RMS thresholds to source-specific hysteresis built from a bounded adaptive noise floor, minimum speech evidence, a speech tail, and a hard turn deadline. Configuration has production defaults and a remote rollback flag.

The backend adds an independent source watchdog. If a segment has published text or audio but receives no newer frame/terminal acknowledgement before its watchdog boundary, it commits the provider buffer through the adapter and reconciles the segment. Provider `server_vad` remains an adapter capability for controlled synthetic/shadow evaluation, not an unconditional production switch.

The alternative—enable `server_vad` for all users immediately—is rejected because prior production-like evidence shows worse finalization for this provider/configuration and would make rollback depend on another desktop release.

### 3. Treat terminal frames as control-plane work

Desktop and backend queues separate terminal intent from coalescible interim audio. Obsolete partial revisions may be merged or dropped under pressure, but the latest unsent audio is folded into a terminal frame and the terminal item gets reserved capacity. The server returns an idempotent terminal acknowledgement containing segment ID/revision; reconnect resends an unacknowledged terminal frame with the same identity.

If the backend cannot accept terminal work within the bounded admission deadline, it emits an explicit degraded event and source recovery instead of silently returning success. This is preferable to increasing queue sizes, which only hides overload and increases latency.

### 4. Separate immutable confirmed turns from the active draft

The Web reducer maintains confirmed turns and at most one active draft per source. A final revision atomically replaces its matching draft. Adjacent display joining may concatenate text for readability but cannot copy a draft state onto a confirmed turn or merge across different segment identities into one mutable lifecycle. Duplicate, delayed, or replayed revisions are ignored by segment ID and monotonic revision/terminal precedence.

An incomplete watchdog result is terminal for presentation but is not provider-confirmed. It may preserve the last stable text with a neutral recovery label and must not trigger an answer or billing.

The alternative—continue deriving lifecycle from the last item in a visually joined card—is rejected because display grouping must not control business state.

### 5. Recover only the affected source

Provider timeout, missing completion, sequence gap, or terminal admission failure closes and recreates only the microphone or system-output provider session. The other source continues. The active segment is resolved once as final when the provider supplied completion, otherwise as incomplete; late events from the retired generation are discarded.

Recovery uses bounded retries with jitter and a circuit state exposed to runtime health. Infinite retry loops and whole-interview teardown are rejected because both amplify outages and remove the user's unaffected channel.

### 6. Preserve explicit-only answer semantics

Final interviewer text updates the visible conversation and the source available to the quick-answer action. No ASR final, watchdog final, candidate detection, or recovery event creates an answer task. Only the existing explicit quick-answer, screenshot-answer, or manual-input actions may call the answer service and consume points.

### 7. Gate release on end-to-end commercial metrics

Privacy-safe telemetry records capture-to-send, queue wait, ASR first text, stop-to-terminal, backend publish, frontend render, finalization reason, retries, terminal resend/ack, and stuck-turn recovery counts. It excludes raw audio and transcript text.

Release fixtures and controlled production canaries target:

- visible interim first text P95 <= 1.5 seconds;
- detected stop to terminal transcript P95 <= 2.0 seconds and P99 <= 4.0 seconds;
- no active “转写中” state beyond 8 seconds without an explicit degraded/incomplete transition;
- zero lost terminal frames in queue saturation/reconnect regression tests;
- no answer task or point charge without an explicit user action.

These are release gates for controlled fixtures and monitored canaries, not guarantees over every third-party network or audio device.

### 8. Prefer isolated Beta, with an explicit resource-constrained direct-canary exception

The optimized backend and Web are deployed under Compose project `offersteady-beta` with dedicated host ports, PostgreSQL and Redis volumes, environment file, migration state, and OSS environment label. Caddy exposes it as `https://beta.mianshiwen.cn`; the production `mianshiwen.cn` route and `compose` project remain unchanged. Beta starts with an empty database plus synthetic test data and never clones production user, payment, transcript, or material data.

Payment callbacks and production release-manifest publication are disabled in Beta. SMS and AI providers may use the same server-side provider accounts only through a separate Beta environment configuration and are still subject to normal cost/rate limits. Beta cookies, JWT issuer/audience where supported, CORS origins, and storage namespace are distinct so a Beta session cannot authenticate against production accidentally.

End-to-end audio verification uses a separately labelled, signed/notarized Beta companion configured for the Beta API and update manifest. The production bundle identifier and production download manifest remain stable; the Beta bundle identifier/name is distinct so it can coexist and receives separate macOS permissions.

Promotion is normally an explicit human approval after Beta acceptance. If the operator explicitly declines a parallel Beta because the current production host lacks safe CPU or memory headroom, production may instead receive a compatibility-first direct canary after the complete local suites pass. That exception MUST record the previous commit/images/manifest, keep the backend watchdog disabled initially, deploy the backward-compatible backend before Web, verify old companions, and publish a new signed companion manifest only after production health checks pass. The same tested source commit is used throughout and each layer retains an immediate rollback. Mounting a test Web against the production backend remains rejected.

## Risks / Trade-offs

- [Adaptive endpointing clips soft trailing words] -> Keep pre-speech/tail buffers, hysteresis, source-specific fixtures, and a remote rollback to the current segmenter constants.
- [Backend watchdog races a delayed desktop final] -> Use the same segment identity, terminal precedence, generation tokens, and idempotent acknowledgements.
- [Forced recovery preserves incomplete wording] -> Label it as incomplete rather than confirmed and never use it to trigger billing or answers automatically.
- [Old companions cannot provide the new local state/ack fields] -> Backend watchdog and Web monotonic projection remain backward compatible; the manifest recommends the new desktop version without blocking an active interview.
- [Additional metrics increase load] -> Use counters/histograms and sampled timing envelopes without transcript/audio payloads; verify CPU and Redis command rate under concurrent synthetic sessions.
- [Changing both desktop and backend complicates rollback] -> Feature flags independently control adaptive endpointing, backend watchdog, and terminal acknowledgement enforcement.
- [Beta competes with production for server CPU and memory] -> Apply CPU/memory limits, keep Beta at zero or one active test interview, and stop Beta automatically outside the acceptance window; abort testing if production health thresholds regress.
- [Beta hostname is not yet resolvable] -> Add an A record for `beta.mianshiwen.cn` to the current server before public acceptance and let Caddy obtain HTTPS; do not fall back to a production path prefix.

## Migration Plan

1. Implement and verify protocol, desktop, backend, and Web changes locally without changing production.
2. Use isolated Beta when the host has safe headroom; otherwise record the operator's explicit direct-canary approval and keep all parallel Beta containers stopped.
3. Record the current production commit, images, configuration flags, and companion manifest before promotion.
4. Deploy the tested commit in compatibility-first order: backend with watchdog disabled, then Web; verify current production companions and health after each step.
5. Publish the newly signed/notarized production companion only after server-side compatibility checks pass, then run the operator's end-to-end acceptance and monitored canary.
6. On regression, restore the previous production images/manifest and independently disable watchdog, acknowledgement enforcement, or adaptive endpointing flags.

## Open Questions

None blocking implementation. Exact per-source noise multipliers and watchdog intervals are configuration values selected from synthetic and authorized meeting-platform fixtures, then tuned by canary telemetry rather than hard-coded as product promises.
