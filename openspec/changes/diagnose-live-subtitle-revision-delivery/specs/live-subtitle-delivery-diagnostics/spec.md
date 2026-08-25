## ADDED Requirements

### Requirement: Revision-level subtitle trace
The diagnostic build SHALL correlate every non-final transcript revision with `session_id`, `utterance_id`, `segment_id`, `revision`, `event_id`, `channel`, and `text_length`, and SHALL record every reliably observable R0–R13 stage without storing transcript text.

#### Scenario: One partial traverses the delivery chain
- **WHEN** Qwen emits a non-empty Partial revision for an enabled diagnostic session
- **THEN** the same event and revision identifiers are observable at Qwen receipt, event creation, Redis XADD/XREAD, SSE yield, Browser receive/parse, store update, React commit, and paint confirmation

#### Scenario: A stage cannot be measured reliably
- **WHEN** the runtime cannot obtain a trustworthy timestamp for a requested stage such as the underlying HTTP chunk write
- **THEN** that stage is reported as unavailable and is not replaced with a timestamp from another stage

### Requirement: Diagnostic isolation and privacy
The system MUST keep the Browser fine-grained diagnostics and overlay disabled for normal sessions, MUST bound trace records and acknowledgement keys, and MUST NOT persist raw audio, transcript text, resume content, JD content, knowledge content, or screenshots in diagnostic records.

#### Scenario: Normal commercial session
- **WHEN** a session is not explicitly enabled for subtitle diagnostics
- **THEN** the user-visible page and realtime delivery behavior remain unchanged and the diagnostic overlay is absent

#### Scenario: Diagnostic retention reaches its bound
- **WHEN** the configured per-session revision limit is reached
- **THEN** additional diagnostic detail is dropped or rotated without delaying or dropping product transcript events

### Requirement: Visibility-qualified browser evidence
The Web diagnostic SHALL record `document.visibilityState` for Browser receive, state update, React commit and paint confirmation, and formal latency distributions MUST include only `visible` samples.

#### Scenario: Page becomes hidden
- **WHEN** a Partial revision arrives while the interview page is not visible
- **THEN** the revision remains in raw diagnostic counts but is excluded from formal P50/P95/P99/MAX latency calculations

### Requirement: Revision continuity accounting
The diagnostic report SHALL compare per-utterance revision counts at Qwen, Redis, SSE, Browser parse, Browser store, React commit and paint, and SHALL report loss rates and all revision gaps over 500ms, 1000ms and 3000ms.

#### Scenario: Browser renders fewer revisions than it receives
- **WHEN** Browser parse records 12 revisions for an utterance but paint confirms only 3 effective revisions
- **THEN** the report shows Qwen/Redis/SSE/Browser/Render counts separately and attributes the missing revisions after Browser receive rather than to Qwen

### Requirement: Non-invasive debug overlay
An explicitly enabled diagnostic Web page SHALL show the latest stage ages, current revision, stage revision counts, and visibility without changing transcript store updates or subtitle presentation behavior.

#### Scenario: Tester observes a stalled subtitle
- **WHEN** the tester keeps the enabled page visible and a subtitle appears stalled
- **THEN** the overlay independently shows whether Qwen, SSE, Browser receive, store and paint counters are still advancing

### Requirement: Real-chain diagnostic acceptance
The final diagnostic run MUST use real Electron System Audio, the configured live Backend, real Redis, real Qwen Realtime ASR, the actual SSE endpoint and a visible real Web interview page with Microphone disabled, and MUST collect at least 50 System utterances.

#### Scenario: Formal test completes
- **WHEN** at least 50 visible System utterances have traversed the real chain
- **THEN** the report answers whether Qwen, SSE, Browser and React are continuously streaming, provides revision intervals and delivery latency distributions, identifies the three largest measured bottlenecks, and includes one content-redacted revision waterfall

#### Scenario: Synthetic or fallback infrastructure is detected
- **WHEN** audio frames are simulated, Redis falls back to memory, Qwen is mocked, or the page is hidden
- **THEN** the affected samples are rejected from the formal acceptance result
