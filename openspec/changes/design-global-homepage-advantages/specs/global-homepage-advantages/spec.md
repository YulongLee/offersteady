## ADDED Requirements
### Requirement: Evidence-based anonymous product comparison
The homepage SHALL compare OfferSteady with three selected actual peer products between capabilities and pricing, using partially masked real competitor labels and official-source evidence.
#### Scenario: Visitor reads comparison
- **WHEN** the section renders
- **THEN** it highlights verified OfferSteady short-term plans, shows reviewed peer pricing and capabilities, and distinguishes unverified data from absent public listings
- **AND** it does not claim lowest monthly price, hide different plan terms, expose full competitor names or assert unsupported superiority
### Requirement: Responsive and isolated design
The section SHALL use accessible markup, existing navigation and responsive layout without core behavior changes.
#### Scenario: Feature-first comparison
- **WHEN** a visitor compares products
- **THEN** eight capability rows precede a single grouped pricing row, and the top callout accurately states the day-pass duration and Copilot allowance

#### Scenario: Mobile visitor views table
- **WHEN** the viewport is narrow
- **THEN** phone layouts show stacked comparison cards and tablet layouts allow contained table scrolling without full-page horizontal overflow
#### Scenario: Approved Global deployment
- **WHEN** the approved comparison is deployed
- **THEN** only Global Web is updated from the verified current release, a rollback version is retained, and China and core services remain unchanged
