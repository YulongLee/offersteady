## ADDED Requirements

### Requirement: Build only from the verified actual Global backend baseline
The release SHALL re-read the target component's actual running image/container, source/Prompt inventory, routes, effective models/configuration, deployment identity and non-target component identities. It SHALL NOT infer source from `current`, old directories, mutable tags or health version text. Candidate changes SHALL be restricted to approved prefetch nodes in Chat/Realtime plus the scheduler module; all non-target source/Prompt hashes and non-approved target nodes SHALL match the actual baseline. Unexpected writable-layer or runtime drift SHALL stop release until explained and protected.

#### Scenario: Mixed development tree contains unrelated regional changes
- **WHEN** Git source differs from actual Global behavior beyond approved prefetch work
- **THEN** only approved nodes are migrated onto the actual-image source and unrelated regional functions, routes, prompts and optimizations remain preserved

### Requirement: Freeze and verify a synthetic-tested immutable candidate
Before production mutation the release SHALL freeze candidate payload/proofs and an immutable previous-image rollback, pass isolated synthetic concurrency/cache/cleanup/quick/detail/Global regressions, and perform an offline read-only actual-candidate probe. It SHALL report observed work/read counts, timing and grounding behavior without claiming measured production P95. Probe execution SHALL NOT start application lifecycle or access production databases, providers, user data or persistent writes.

#### Scenario: Candidate preservation or synthetic check fails
- **WHEN** any required regression, probe, route/source/config/model comparison or payload-integrity check fails
- **THEN** production remains on the original Global Backend and the failing evidence is recorded

### Requirement: Cut over only Global backend when protected work is absent
Immediately before a cutover the release SHALL revalidate runtime/candidate identity and fail closed on active or indeterminate ordinary/written/mock sessions, desktop/page leases, audio tracks, pending generations/screenshots or material work. It SHALL update only Global Backend using an immutable image overlay while preserving the effective Compose order/project directory, environment, HostConfig, mounts and every other component. Existing Global mock enabled false SHALL remain false.

#### Scenario: Active interview or uncertain gate result
- **WHEN** protected activity exists or an activity check cannot complete authoritatively
- **THEN** no Backend restart or switch occurs, and production records are not deleted or altered to manufacture an idle window

#### Scenario: Idle verified backend cutover
- **WHEN** current identities match the frozen baseline and all immediate protected-work gates pass
- **THEN** only Global Backend switches to the approved candidate and CN, Global Web/assistants/Admin/worker/databases retain their prior runtime identities

### Requirement: Verify release and restore its owned previous image on failure
Post-switch verification SHALL inspect health/restart, runtime source/Prompt/routes, effective configuration/models/feature flags, anonymous public entrypoints, non-target component identities and short deidentified error summaries. Failure recovery SHALL restore the frozen previous Backend image/configuration only after checking release ownership, absence of later deployments and protected-work safety; it SHALL verify the restored state and SHALL NOT overwrite unrelated later releases. Release records SHALL distinguish completed checks from real-load P95 and physical-client acceptance not performed.

#### Scenario: Candidate fails post-switch verification
- **WHEN** candidate verification fails and safe recovery ownership/activity checks pass
- **THEN** only this release's Global Backend is restored to the immutable previous image with preserved config, and recovery checks and actual outcomes are recorded

#### Scenario: Successful release with no real-user test
- **WHEN** health and preservation checks pass but no real user interview or sustained production comparison has been measured
- **THEN** release is recorded as deployed with those acceptance limits explicit, without asserting hardware or P95 improvement has already been proven
