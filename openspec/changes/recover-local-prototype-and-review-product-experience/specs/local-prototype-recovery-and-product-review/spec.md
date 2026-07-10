## ADDED Requirements

### Requirement: Local prototype must be restorable to an approved baseline
The system SHALL provide a recoverable local Web prototype baseline that preserves the approved page structure, core interaction order, and prototype wording across the primary product journey.

#### Scenario: Restore broken local prototype
- **WHEN** the local prototype becomes unavailable, visually broken, or diverges from the approved journey
- **THEN** the team MUST restore a runnable local baseline before continuing new product or engineering changes

#### Scenario: Protect approved prototype behavior during recovery
- **WHEN** a recovery action is taken for the Web prototype
- **THEN** it MUST preserve the approved user journey for landing, login, library, interview preparation, live interview, billing, download, and usage guidance rather than silently redesigning those flows

### Requirement: Product review must inspect the full prototype journey
The system SHALL define a product review pass that checks the complete prototype journey page by page and identifies whether each major flow remains usable, understandable, and aligned with the approved product intent.

#### Scenario: Review major product paths
- **WHEN** a prototype review is performed
- **THEN** it MUST cover at least the landing page, login or account entry, materials management, interview preparation, live interview workspace, points or billing area, download area, and user guidance area

#### Scenario: Record review output
- **WHEN** a prototype review finds issues
- **THEN** each issue MUST be classified as either an immediate recovery item or a later product decision item

### Requirement: Engineering integration must not silently rewrite prototype UX
The system SHALL preserve a clear boundary between prototype UX and engineering integration so that backend contracts, upload adapters, or infrastructure changes do not silently alter approved prototype interactions.

#### Scenario: Backend integration conflicts with prototype UX
- **WHEN** a backend or adapter change conflicts with the approved prototype behavior
- **THEN** the implementation MUST prefer a compatibility layer, fixture adjustment, or explicit follow-up change instead of silently rewriting the prototype UX

#### Scenario: Recovery documents protected baseline
- **WHEN** the prototype baseline is restored
- **THEN** the project MUST document which prototype behaviors are protected and should not be changed without a new approved OpenSpec change
