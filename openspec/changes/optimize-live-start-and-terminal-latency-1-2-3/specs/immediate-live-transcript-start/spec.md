## ADDED Requirements

### Requirement: Capture-ready sources admit first speech promptly
The desktop SHALL keep microphone and system-audio readiness independent and SHALL emit recognizable first speech without an avoidable startup suppression interval after a source reports capture-ready.

#### Scenario: Computer audio starts after interview entry
- **WHEN** system capture is ready and recognizable authorized speech begins
- **THEN** the desktop emits the first speech frame within the bounded attack and buffering window without waiting for a reconnect or hard recovery timer

#### Scenario: Ready source is silent
- **WHEN** a capture graph is open but contains silence
- **THEN** the source remains ready without emitting fake speech frames or triggering recovery churn

### Requirement: Provider readiness is reconstructed before first use
The backend SHALL idempotently prepare enabled provider sources on interview start and authenticated desktop attachment while preserving a single-flight lazy path for the first frame.

#### Scenario: Desktop attaches to an already-live interview
- **WHEN** a publisher attaches after process-local provider sessions are absent
- **THEN** both enabled sources are rewarmed and a racing first frame shares the same source creation

### Requirement: Browser initial delivery is bounded and stable
The Web and backend SHALL establish one authoritative session stream whose initial state and subsequent transcript events do not depend on repeated five-second fallback cycles.

#### Scenario: A new live page subscribes
- **WHEN** the page owns the active lease and opens the session stream
- **THEN** it receives an authoritative initial snapshot promptly and keeps one leader-owned subscription

#### Scenario: Stream recovery uses fallback
- **WHEN** an SSE connection fails and an HTTP snapshot recovers visible state
- **THEN** reconnect backoff is retained until a real stream snapshot succeeds and fallback does not create a tight reconnect loop

### Requirement: First-visible latency is verifiable
The release SHALL record content-free stages from first meaningful capture through provider partial, session event, SSE, and browser paint and SHALL target speech-start-to-first-visible P50 at or below 1.5 seconds and P95 at or below three seconds.

#### Scenario: Local acceptance exercises both sources
- **WHEN** authorized microphone and system speech are played after a fresh interview entry
- **THEN** the report contains per-source first-visible distributions, reconnect counts, and queue bounds without audio or transcript content
