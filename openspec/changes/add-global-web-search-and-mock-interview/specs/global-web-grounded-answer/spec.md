## ADDED Requirements

### Requirement: Opt-in detailed web answer
The Global interview toolbar SHALL show an eligible member's web toggle beside auto-answer, off by default. Simple answers MUST complete before waiting for search; detailed answers SHALL show search status, safe source links, or an honest local fallback. Ineligible users SHALL see the seven-day membership requirement.

#### Scenario: Slow or unavailable search
- **WHEN** web retrieval is slow or fails
- **THEN** simple text stays readable and completed; detailed generation falls back without blocking normal quick answer

#### Scenario: Disable during retrieval
- **WHEN** the user turns web mode off
- **THEN** only the old web task is cancelled, its visible text is preserved, and a new ordinary answer can start without being overwritten by late events

### Requirement: Provider and privacy isolation
Global web answers MUST use configured Global credentials and non-thinking requests. Only a normalized question and bounded non-sensitive context SHALL go to search, not full resumes, screenshots or audio. Source text SHALL be treated as untrusted evidence. CN behavior MUST remain unchanged.

#### Scenario: Provider rejects a request
- **WHEN** the Global provider is unavailable or rejects web tools
- **THEN** a clear fallback is shown and the system does not fabricate source citations or retry with deep thinking
