## 1. Baseline And Contracts

- [x] 1.1 Capture a synthetic baseline for microphone pauses, system-output background noise, long continuous audio, reconnect, and queue pressure using the current production-compatible path
- [x] 1.2 Extend the shared realtime protocol with backward-compatible optional turn state, finalization reason, source generation, and terminal acknowledgement fields
- [x] 1.3 Add protocol transition tests proving terminal precedence, revision monotonicity, old-client compatibility, and explicit-only answer triggering

## 2. Desktop Commercial Endpointing

- [x] 2.1 Refactor the desktop speech segmenter into an explicit per-source idle/speaking/tail/committing/terminal state machine
- [x] 2.2 Implement bounded adaptive noise floors, source-specific hysteresis, buffered tails, and hard turn deadlines without persisting audio
- [x] 2.3 Prioritize terminal frames in WebSocket and HTTP fallback queues, preserve latest unsent audio, and resend unacknowledged terminals idempotently
- [x] 2.4 Add remote/runtime feature flags and source-health metrics for endpointing mode, finalization reason, terminal age, resend, and acknowledgement
- [x] 2.5 Add desktop synthetic regressions for soft speech, ordinary pauses, meeting-platform noise, uninterrupted signal, reconnect, queue saturation, and stop/flush
- [x] 2.6 Run desktop focused tests, typecheck, and production build before proceeding to backend changes

## 3. Backend Terminal Delivery And Watchdog

- [x] 3.1 Change per-source ingress admission so obsolete partials coalesce or yield reserved capacity while terminal work receives explicit acceptance or degraded failure
- [x] 3.2 Add idempotent terminal acknowledgement and generation checks so reconnect/replay processes one terminal intent at most once
- [x] 3.3 Add a provider-adapter finalization boundary that supports Manual commit now and keeps provider VAD replaceable/configurable
- [x] 3.4 Implement a bounded source watchdog that commits abandoned active turns, reconciles authoritative completion, or publishes one incomplete terminal state
- [x] 3.5 Recover only the affected ASR source with bounded retries/jitter and reject late events from retired generations
- [x] 3.6 Add backend metrics for stop-to-terminal latency, finalization reason, terminal admission/resend, incomplete recovery, queue pressure, and source reconnects without content payloads
- [x] 3.7 Add backend regressions for missing desktop final, missing provider completion, full queue, duplicate terminal, late provider event, source-isolated recovery, and no implicit answer/billing
- [x] 3.8 Run backend focused tests and synthetic concurrency/load checks before enabling any new behavior by default

## 4. Web Monotonic Transcript Experience

- [x] 4.1 Separate confirmed transcript turns from active per-source drafts in the Web reconciliation model
- [x] 4.2 Make visual adjacent-turn joining independent of lifecycle and enforce segment revision plus terminal precedence during SSE replay/reconnect
- [x] 4.3 Present recovered incomplete turns as terminal neutral states without continued animation, automatic answer generation, or point consumption
- [x] 4.4 Add Web regressions for final-then-partial, adjacent new speech, duplicate/out-of-order replay, reconnect, two-source overlap, and no flicker
- [x] 4.5 Run Web focused tests, typecheck, and production build before integration testing

## 5. End-To-End Commercial Verification

- [x] 5.1 Add or update privacy-safe AI eval fixtures proving transcription and question identification never start answer generation without explicit user action
- [x] 5.2 Run desktop-to-backend-to-Web synthetic scenarios for quiet speech, Mandarin pauses, system noise, long speech, queue saturation, network loss, provider timeout, and session recovery
- [ ] 5.3 Measure visible interim TTFT, detected stop-to-terminal P50/P95/P99, frontend render, stuck-turn rate, terminal loss, CPU, Redis commands, and queue depth against the specified release gates
- [x] 5.4 Run complete backend, Web, desktop, protocol, AI eval, typecheck, build, and OpenSpec strict validation suites
- [x] 5.5 Update realtime runtime, troubleshooting, performance baseline, compatibility, upgrade, and rollback documentation with measured results

## 6. Isolated Beta Environment

- [x] 6.1 Add a dedicated Beta Compose project/configuration with separate ports, PostgreSQL/Redis volumes, environment identity, OSS namespace, resource limits, and production-side-effect guards
- [x] 6.2 Add Beta deployment, health, teardown, and production-non-regression scripts that never run production Compose mutation commands
- [x] 6.3 Add a Caddy Beta virtual-host template and verify DNS resolution; keep the Beta stack stopped after the user selected the resource-constrained direct-canary path
- [x] 6.4 Build, sign, notarize, and verify production macOS arm64/x64 companions; retain the current Windows release until an Authenticode identity is available
- [x] 6.5 Run complete local smoke/load checks and record the tested commit, package digests, production rollback baseline, resource caps, and known limitations

## 7. User Acceptance And Production Promotion

- [x] 7.1 Keep production on its existing commit/images/manifest while local release verification runs; parallel Beta remains stopped by explicit user decision
- [x] 7.2 Address local verification findings and repeat focused plus full commercial verification without changing production
- [x] 7.3 Obtain explicit user approval for the resource-constrained direct-canary strategy and its known Windows signing limitation
- [ ] 7.4 Promote backward-compatible backend then Web artifacts, verify production, and only then publish the tested production macOS companion manifest
- [ ] 7.5 Enable bounded feature canaries, expand only after production SLOs pass, commit/push scoped files, and record previous/current artifacts plus rollback switches
