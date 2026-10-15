## ADDED Requirements

### Requirement: Lead promptly and coalesce intermediate revisions
Ordinary interviewer question prefetch SHALL start the first eligible stable question promptly and retain only the newest pending update per owner/session/question. Intermediate updates SHALL use a bounded quiet window and maximum wait, without changing transcript or question-stable event publication.

#### Scenario: A burst extends one question
- **WHEN** many newer partial revisions arrive within the quiet window
- **THEN** the leading revision is eligible immediately, obsolete pending revisions are replaced, and the latest pending revision becomes eligible within the maximum wait

#### Scenario: Final text equals a prior stable prefix
- **WHEN** a newer final revision has the same text as the last stable partial
- **THEN** final revision/finality still reaches prefetch scheduling without waiting for another text change

### Requirement: Final preparation has bounded priority
Final prefetch SHALL become eligible immediately and SHALL be preferred over ordinary pending updates. An idle worker SHALL be allowed to start a newer final while the same key's obsolete partial is still running, with at most two running tasks per key and two globally. Ordinary partial work SHALL remain single-flight per key.

#### Scenario: An obsolete partial is slow
- **WHEN** an old partial retrieval remains blocked and another worker is idle when final arrives
- **THEN** final can complete without waiting for the old retrieval, and the old result cannot publish over final

#### Scenario: All workers are busy
- **WHEN** both workers are blocked and many newer revisions arrive
- **THEN** running work stays bounded and only the latest eligible pending item per key is retained without creating more workers

### Requirement: Bound state and clean up safely
The scheduler SHALL bound tracked keys and queued age, suppress superseded revisions at safe execution boundaries, and revoke session work on cleanup/shutdown. It SHALL NOT terminate running synchronous IO or cancel unrelated cold persistence/usage work. External operations SHALL run outside the scheduling lock.

#### Scenario: Session ends while work exists
- **WHEN** session cleanup or scheduler shutdown occurs during queued or running prefetch
- **THEN** pending work is discarded, stale tokens reject results, and unrelated realtime operations retain their existing behavior

#### Scenario: Delayed partial follows final
- **WHEN** an older or equal partial observer runs after a final observer
- **THEN** final stable state is not overwritten and no obsolete prefetch is admitted

#### Scenario: Cleanup races an observer or resets a live session
- **WHEN** cleanup overlaps an observer before state update or submission, or an old cold observer begins after a non-retired reset
- **THEN** the old observer cannot recreate cleared stable state or enqueue prefetch in the new session generation

### Requirement: Keep the explicit answer path responsive
User-triggered quick answers SHALL keep the current non-waiting prepared-cache lookup/fallback and independent detailed retrieval path. Prefetch scheduling SHALL NOT block transcript publication, audio processing or explicit answer startup.

#### Scenario: User clicks during a slow prefetch
- **WHEN** a user starts an answer while optional prefetch is blocked or delayed
- **THEN** quick startup does not wait for that work and detailed retrieval still uses the authoritative current materials
