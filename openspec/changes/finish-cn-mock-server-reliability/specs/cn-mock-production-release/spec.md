## ADDED Requirements

### Requirement: Release only reviewed CN mock increments over actual runtime
The authorized CN release SHALL derive Backend and Web from their freshly verified actual fixed images. Backend SHALL change only the five approved mock Python inputs, adding only diagnostics. Dependencies, settings, prompts, full API schema, billing, deadlines and database schema SHALL remain equal. Web SHALL retain every old asset and preserve unrelated functions, static content, SEO, nginx and CSP, changing only approved mock behavior and necessary versioned references. Companion, Global and non-target containers SHALL remain unchanged.

#### Scenario: An unexpected input drifts
- **WHEN** runtime ownership, source, configuration, dependencies, static bytes, controller or non-target signatures differ from the frozen baseline
- **THEN** automatic switching stops without accepting a replacement baseline or overwriting unrelated changes

### Requirement: Protect all user work at every cutover
Preparation, preflight and each component switch SHALL check the existing seven read-only protected-work gates and TCP8000 gate. Active interviews, preparation leases, audio, answers, document/resume tasks, financial work, unknown states and read failures SHALL block cutover. The original financial orphan classification anchor SHALL remain fixed at 1792600214792 independently of the current target-owner snapshot. The controller MUST NOT end, clear, reclassify or bypass user work to enable release.

#### Scenario: A user starts while candidates are being prepared
- **WHEN** any protected-work or TCP gate becomes busy or unavailable before a switch
- **THEN** that switch is deferred with the existing service retained and repeated only after unchanged-scope gates pass

### Requirement: Validate fixed candidates and preserve safe recovery
Actual candidate images SHALL pass offline, read-only probes using server-local private configuration and synthetic data. Web executable behavior, imports and preserved report/export functions SHALL be checked against the assembled package. Release SHALL freeze ownership/configuration and journal created containers, retain exact Backend rollback and cache-compatible Web rollback, and perform full runtime/public verification and redacted error observation. No real provider, physical audio, paid session or production load test SHALL be invoked.

#### Scenario: Candidate or cutover fails
- **WHEN** candidate validation fails or cutover cannot complete
- **THEN** no unvalidated candidate is accepted, and recovery uses only proven release-owned containers and fixed rollback images under the same user-work guards; unresolved drift or recovery failure is reported
