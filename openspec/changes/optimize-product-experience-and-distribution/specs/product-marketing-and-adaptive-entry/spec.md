## ADDED Requirements

### Requirement: Public entry communicates product value without a single-platform boundary
The public entry SHALL explain personalized interview assistance, supported input modes, concrete answer sources, cross-device use and privacy controls before discussing desktop platform architecture. It MUST NOT imply that the product is limited to macOS or claim an unreleased platform capability as available.

#### Scenario: Visitor reviews the hero content
- **WHEN** a visitor opens the public landing page
- **THEN** the hero explains the interview outcome and primary advantages without describing Mac as the product boundary

#### Scenario: Windows capability is not released
- **WHEN** a Windows build or required capture capability is not available in the release manifest
- **THEN** the page labels it as unavailable or planned instead of presenting it as downloadable and complete

### Requirement: Marketing claims map to observable product evidence
Each primary marketing claim SHALL link to or be supported by an observable product state, example or boundary disclosure. AI output MUST remain labelled as advice and MUST NOT promise fabricated experience or guaranteed interview outcomes.

#### Scenario: Visitor inspects personalized-answer evidence
- **WHEN** the landing page claims answers use personal context
- **THEN** it shows an example with concrete resume, JD or knowledge-source labels and the AI-advice boundary

### Requirement: Authenticated entry uses task-aware and time-safe language
The authenticated home SHALL prioritize the user's actionable interview state. Time-of-day text SHALL use the user's available IANA timezone and SHALL fall back to neutral wording when the timezone or render context is uncertain.

#### Scenario: User has an interview in preparation
- **WHEN** the authenticated user opens home with an unfinished interview
- **THEN** the primary heading invites the user to continue that interview rather than showing only a generic greeting

#### Scenario: Local time cannot be determined reliably
- **WHEN** the client cannot determine a reliable local timezone or hydration would produce conflicting time text
- **THEN** the interface uses the neutral greeting “你好” and a task-based next action

