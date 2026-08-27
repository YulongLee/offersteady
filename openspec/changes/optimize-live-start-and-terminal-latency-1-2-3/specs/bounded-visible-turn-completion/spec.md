## ADDED Requirements

### Requirement: Residual noise cannot keep a turn open indefinitely
The desktop SHALL identify last meaningful speech per source and SHALL emit one terminal intent within a bounded release window when only residual energy remains.

#### Scenario: System speech ends over steady residual noise
- **WHEN** recognized system-audio speech falls to a bounded fraction of the turn peak while low residual energy continues
- **THEN** the source enters its tail and emits a terminal frame within the maximum release window

#### Scenario: Speech resumes during the tail
- **WHEN** strong speech evidence returns before the release deadline
- **THEN** the source resumes the same segment without truncating the continuation

### Requirement: Visible completion remains bounded after terminal admission
The backend SHALL supervise a committing segment until provider final or one explicit incomplete terminal and SHALL NOT expose the full provider hard timeout as an indefinite visible state.

#### Scenario: Provider final completes normally
- **WHEN** provider completion arrives within the source terminal budget
- **THEN** one final revision replaces the draft and the temporary recovery state is cleared

#### Scenario: Provider completion is missing
- **WHEN** a committing segment exceeds the watchdog deadline
- **THEN** the latest stable partial becomes one incomplete terminal, only the affected source is recreated, and later events cannot reopen the segment

#### Scenario: Following speech arrives while committing
- **WHEN** the next utterance begins before the prior provider completion
- **THEN** bounded subsequent audio is preserved and proceeds after the prior segment terminalizes

### Requirement: Browser presentation reflects turn lifecycle truthfully
The Web SHALL distinguish active transcription from bounded terminal confirmation and SHALL render final and incomplete states monotonically using the existing transcript row.

#### Scenario: Terminal intent awaits provider confirmation
- **WHEN** the backend reports a committing turn
- **THEN** the row stops claiming active speech and shows a bounded confirming state

#### Scenario: Partial becomes abandoned
- **WHEN** no authoritative terminal arrives by the recovery boundary
- **THEN** the row becomes an explicit incomplete terminal without continued animation or automatic answer/billing side effects

### Requirement: User-perceived stop latency is measured
The release SHALL measure from last meaningful speech rather than only from terminal-frame creation and SHALL target last-meaningful-speech-to-visible-terminal P95 at or below 1.5 seconds, P99 at or below three seconds, and no unlabelled transcribing state beyond four seconds.

#### Scenario: Local stop-latency acceptance completes
- **WHEN** authorized clean speech, residual-noise speech, short pauses, and consecutive utterances are exercised
- **THEN** the report contains per-source release, provider completion, SSE, render, incomplete, and lost-terminal metrics without content payloads

### Requirement: Companion 1.2.3 preserves approved identity and supported-platform behavior
The companion patch SHALL report version 1.2.3 on macOS ARM64, macOS Intel x64, and Windows x64, SHALL use the shared endpointing behavior on every target, and SHALL preserve the existing layout, icon, product name, bundle identifier, signing identity, and production endpoint defaults.

#### Scenario: Local package is built
- **WHEN** the macOS 1.2.3 candidate is packaged for acceptance
- **THEN** metadata and code-sign verification report the approved identity and the running process comes from the 1.2.3 artifact

#### Scenario: Supported production packages are published
- **WHEN** release 1.2.3 is promoted to production
- **THEN** macOS ARM64, macOS Intel x64, and Windows x64 artifacts contain the same shared segmenter/protocol build, platform-specific capture runtimes match their declared architectures, and the manifest switches the three targets together
