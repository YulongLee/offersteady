## ADDED Requirements

### Requirement: Authenticated users can discover the partner program
The authenticated product navigation SHALL show a visually emphasized partner-program entry whenever the partner program is enabled. The entry MUST use the existing design system, remain keyboard accessible and responsive, and MUST NOT cover or delay interview controls.

#### Scenario: Eligible user opens the application
- **WHEN** an authenticated user opens any standard application page while the partner program is enabled
- **THEN** the side navigation shows a prominent “合作伙伴计划” entry with a concise 20% promotion benefit label

#### Scenario: Partner program is unavailable
- **WHEN** the server reports that the partner program is disabled
- **THEN** the navigation does not claim that commission can currently be earned and all interview functions remain unchanged

### Requirement: Existing secondary entry remains valid
The existing Footer partner-program link SHALL remain available as a secondary discovery path and both entries SHALL resolve to the same authenticated partner dashboard.

#### Scenario: User follows either entry
- **WHEN** a user selects the Footer link or the side-navigation activity entry
- **THEN** the application opens the same `/app/partner-program` route without creating a second partner profile
