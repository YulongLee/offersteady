## Context

The production Companion uses a renderer-owned binding poller and a main-process screenshot SSE loop. In normal live operation those loops are intentionally responsive, but multiple application processes can currently share the same persisted device identity because startup does not claim Electron's single-instance lock. A terminal 404/409 screenshot admission response is also handled like a transient transport failure, so stale bindings continue opening SSE and fallback-poll requests. The backend serves realtime and ordinary control traffic from one Uvicorn process, making amplified control reads visible in ordinary API tail latency.

The current audio publisher and ASR gateway have process-local lifecycle state. This change therefore must not attempt a naive multi-worker rollout or alter audio/transcript behavior.

## Goals / Non-Goals

**Goals:**

- Guarantee one Companion process owns a domestic or Global profile at a time.
- Guarantee one in-flight binding read per renderer poller and one screenshot stream owner per main process.
- Distinguish terminal invalid-binding responses from transient network/provider failures.
- Suspend invalid screenshot bindings without delaying detection of a new valid binding.
- Bound repeated identical active-connection reads without returning stale data across a binding transition.
- Preserve current live capture, screenshot delivery, recovery, layout and endpoint contracts.

**Non-Goals:**

- Changing ASR models, audio framing, transcript stabilization, answer generation or billing.
- Adding Uvicorn workers before realtime process-local state is made worker-safe.
- Persisting request payloads, user content, audio, transcripts or screenshots for diagnostics.
- Replacing the current binding API or screenshot SSE protocol.

## Decisions

### Claim Electron's profile-scoped single-instance lock before readiness

The main process will claim `app.requestSingleInstanceLock()` after selecting the edition-specific stable user-data directory and before registering runtime loops. A second launch will restore/focus the existing window and exit before creating polling or capture owners. The lock is naturally isolated between domestic and Global builds because they use different user-data profiles.

Alternative considered: detect duplicate device identities at the backend. That cannot distinguish a legitimate restarted client from simultaneously running local processes and would add server-side leases to a local lifecycle problem.

### Model screenshot admission as eligible, suspended, or transient failure

The screenshot stream loop will retain a single generation owner. A terminal admission response indicating no current binding will enter an invalid-binding suspension state instead of opening the fallback `next` poll. The renderer's authoritative binding transition will notify the main process and increment the screenshot generation, immediately waking the loop for a new valid live binding. Network errors and 5xx responses keep bounded exponential recovery.

Alternative considered: stop forever on any 404/409. That could break rapid consecutive interviews, so suspension must be explicitly woken by binding eligibility changes.

### Keep binding reads single-flight and suppress redundant immediate wakeups

The existing in-flight guard remains authoritative. Visibility and lifecycle wakeups will coalesce into at most one pending immediate poll rather than repeatedly scheduling zero-delay work. Normal live and waiting intervals remain unchanged.

### Protect identical active-connection reads with revision-aware short caching

The backend will cache only successful, content-free active-connection response envelopes for a sub-second bounded interval, keyed by device identity plus manual code and pinned binding/session identifiers. Mutating registration/binding/session transitions invalidate or naturally bypass cached entries through a repository/runtime revision token. If a safe revision signal is unavailable, the implementation will use request coalescing only and will not cache across completed requests.

Alternative considered: generic endpoint rate limiting. Returning 429 to Companion control loops would create additional recovery churn and could delay legitimate preparation-to-live transitions.

### Do not add backend workers in this rollout

The current ASR session and publisher lifecycle contains process-local objects. Worker scaling is deferred until those owners are externalized or requests are session-sticky.

## Risks / Trade-offs

- [Risk] Single-instance handling could hide the existing window behind other applications. → Restore, show and focus the primary window on `second-instance`.
- [Risk] Terminal response classification could suspend a temporarily inconsistent binding. → Only suspend explicit no-binding/terminal admission codes; wake immediately on renderer eligibility transition and application activation.
- [Risk] A cached connection response could mask a rapid state transition. → Keep the bound below one normal poll interval, include pinned identifiers in the key, and invalidate on known mutations.
- [Risk] Existing old Companion versions will continue inefficient polling. → Server protection is backward compatible; publish the new desktop version through the existing non-forced upgrade notice.
- [Risk] Dirty Global worktree changes overlap desktop startup files. → Make minimal hunks, inspect diffs before tests, and do not include unrelated files in the domestic deployment.

## Migration Plan

1. Capture the current domestic deployment commit, image IDs, container IDs and health as rollback evidence.
2. Add regression tests before implementation for duplicate launch, suspended screenshot admission, rapid consecutive binding wakeup, and duplicate active reads.
3. Build and test desktop on supported platforms at source/config level; package the required domestic artifacts using existing signing workflow.
4. Run backend and desktop full test/typecheck/build suites and strict OpenSpec validation.
5. Confirm no active interview, tag rollback images, deploy only required domestic services and release manifest/artifacts.
6. Verify public health, downloads, binding, screenshot, realtime smoke and privacy-safe request metrics.
7. Roll back the affected image/manifest if functional smoke or latency acceptance fails; do not touch database or Redis volumes.

## Open Questions

None. The user approved the P0 scope and requested deployment only when no interview is active.
