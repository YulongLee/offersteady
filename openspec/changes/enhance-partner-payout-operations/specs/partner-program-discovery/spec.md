## ADDED Requirements

### Requirement: The partner program is discoverable only from the public homepage bottom
The public homepage SHALL show a visually distinct, keyboard-accessible partner-program section near the bottom whenever the partner program is enabled. Authenticated desktop and mobile workbench navigation MUST NOT show a partner-program entry, and the change MUST NOT cover or delay interview controls.

#### Scenario: Visitor opens the public homepage
- **WHEN** a visitor opens the public homepage while the partner program is enabled
- **THEN** the homepage bottom shows a “合作伙伴计划” section resolving to the protected partner dashboard

#### Scenario: Authenticated user opens the workbench
- **WHEN** an authenticated user opens any standard application page
- **THEN** neither the desktop side navigation nor mobile workbench navigation shows a partner-program entry

#### Scenario: Partner program is unavailable
- **WHEN** the server reports that the partner program is disabled
- **THEN** the public homepage does not claim that commission can currently be earned and all interview functions remain unchanged

### Requirement: Administrators can enable or pause partner recruitment
The administrator partner view SHALL expose the current partner-program activity state. An administrator with `promotion.manage` SHALL be able to enable or disable public discovery and new enrollment with explicit confirmation and a recorded reason. Disabling MUST preserve existing links, attribution, commission, payout profiles, payout requests and reconciliation access.

#### Scenario: Administrator pauses the activity
- **WHEN** an authorized administrator confirms disabling the partner program
- **THEN** the homepage entry disappears, new join attempts are rejected, the configuration version and audit record advance, and historical partner finance data remains unchanged

#### Scenario: Administrator re-enables the activity
- **WHEN** an authorized administrator confirms enabling the partner program
- **THEN** the homepage entry becomes available again and new users may join without recreating existing partner profiles
