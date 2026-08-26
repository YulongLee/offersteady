## 1. Reproduce Production Failure

- [x] 1.1 Add a deterministic desktop regression for an established system-audio publisher whose ACK progress stops after a high sequence and enters replacement recovery.
- [x] 1.2 Add regressions proving silence after replacement readiness does not create publisher churn and stale transport events cannot recover the current transport.
- [x] 1.3 Add a regression proving exhausted replacement recovery never calls the legacy HTTP frame endpoint and ends in truthful lost health.

## 2. Harden Desktop Recovery

- [x] 2.1 Separate replacement WebSocket readiness from first-media ACK progress and start the ACK deadline only after replacement media is produced or queued.
- [x] 2.2 Preserve single-flight bounded retries, current-transport ACK gating, fresh sequence alignment and per-attempt resource cleanup.
- [x] 2.3 Remove automatic legacy HTTP frame fallback from the production publisher and implement sticky terminal lost state with explicit restart/rebind guidance.
- [x] 2.4 Make system-audio health and capture state follow current send/ACK/buffer evidence so callbacks cannot mask a dead upload path.

## 3. Bound Web Stream Bootstrap

- [x] 3.1 Replace full retained-event enumeration in the initial realtime stream snapshot with authoritative current state plus required latest stateful events.
- [x] 3.2 Add Backend refresh/re-entry tests for bounded bootstrap content, cursor continuity and subsequent incremental updates.
- [x] 3.3 Add or update Web regressions for visible partial revisions, monotonic in-place replacement and degraded/lost capture presentation.

## 4. Version and Verification

- [x] 4.1 Bump shared companion patch version and release metadata to 1.1.3 without changing bundle identifier or realtime protocol 2.0.
- [x] 4.2 Run focused and full Desktop, Backend and Web tests, type checks, production builds, strict OpenSpec validation and diff checks.
- [x] 4.3 Build a local macOS arm64 1.1.3 application, back up the installed app recoverably, install and launch it without updating the public production manifest.
- [x] 4.4 Run a controlled local/production system-audio joint test and record ACK recovery, publisher count, false-online state and subtitle latency evidence without retaining audio or transcript content.
