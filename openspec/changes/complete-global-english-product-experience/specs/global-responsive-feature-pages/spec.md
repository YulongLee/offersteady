## ADDED Requirements

### Requirement: Responsive Global customer routes
The Global application SHALL keep the existing OfferSteady dark-and-green design language while presenting usable navigation, content, forms, cards, tables, dialogs, and primary actions at desktop, tablet, and mobile viewport classes.

#### Scenario: Desktop feature page
- **WHEN** a Global feature route is rendered at a supported desktop width
- **THEN** navigation and primary content use the available space without clipped text, letter-by-letter wrapping, or overlapping actions

#### Scenario: Narrow feature page
- **WHEN** a Global feature route is rendered at a supported tablet or mobile width
- **THEN** navigation and controls adapt without hiding required actions or requiring horizontal page scrolling

### Requirement: Concise component-specific hierarchy
The Global application SHALL use copy lengths and hierarchy appropriate to each component instead of repeating explanatory sentences in navigation, counters, cards, and buttons.

#### Scenario: User scans a page
- **WHEN** a user views a page containing a title, summary cards, empty state, and primary action
- **THEN** each element has a distinct concise label and the primary task is visually identifiable

### Requirement: Global navigation excludes the domestic user manual
The Global application SHALL NOT display the domestic external `User manual` entry in desktop or mobile application navigation. The Global in-product `Product guide` remains available as a separate route.

#### Scenario: User opens the Global workspace
- **WHEN** a Global user views desktop or mobile application navigation
- **THEN** no `User manual` external link is shown and `Product guide` remains available

### Requirement: Route-state regression coverage
Global route verification SHALL cover representative empty, populated, loading, success, and error states where those states exist.

#### Scenario: Release candidate is verified
- **WHEN** a Global Web release candidate is built
- **THEN** route-level tests verify critical copy, actions, and responsive structure for the supported customer journeys
