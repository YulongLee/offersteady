## ADDED Requirements

### Requirement: Faithful anonymous English feedback
The Global homepage SHALL display English translations of the 20 owner-supplied entries with anonymous attribution and no invented ratings, identities, likes, employers or outcomes. Qualifications and improvement requests SHALL remain intact, and an English note SHALL identify translated submissions and edition-dependent experiences/plans.

#### Scenario: Visitor reads the feedback
- **WHEN** a visitor navigates the feedback cards
- **THEN** all 20 entries are reachable in English and both positive experiences and original suggestions remain present
- **AND** the section does not assert independently verified reviews or current Global price endorsements

### Requirement: Responsive accessible rotation
The carousel SHALL display three cards on desktop, two on tablet and one on mobile, with labelled previous, next and play/pause controls. It SHALL rotate at 10-second intervals only while visible and active, pause on hover or hidden document, stop on focus/manual interaction, and default to no autoplay with reduced motion.

#### Scenario: Visitor navigates manually
- **WHEN** the visitor activates next, previous or swipes
- **THEN** the entries change with wraparound and automatic rotation stops until explicitly restarted

#### Scenario: Visitor reads without motion
- **WHEN** reduced motion is preferred or the visitor pauses or focuses the module
- **THEN** automatic rotation is stopped and manual navigation remains available

#### Scenario: Section is not visible
- **WHEN** the page is hidden or the section is outside the viewport
- **THEN** no automatic slide changes occur

### Requirement: Isolated homepage enhancement
The feedback section SHALL appear after comparison and before pricing, match the existing Global styling, and add no API requests, dependencies or changes to China/authenticated workflows. Static homepage HTML SHALL expose the same feedback without requiring JavaScript.

#### Scenario: Browser does not execute JavaScript
- **WHEN** the initial homepage HTML is read
- **THEN** the feedback text and qualification note remain accessible in an expandable section
