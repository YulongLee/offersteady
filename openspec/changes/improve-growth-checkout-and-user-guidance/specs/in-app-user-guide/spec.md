## ADDED Requirements

### Requirement: Authenticated application provides a dedicated user guide
The application SHALL expose an “使用说明” navigation item and protected `/app/guide` route. The guide SHALL be readable on desktop and mobile without covering an active interview unexpectedly.

#### Scenario: User opens the guide from application navigation
- **WHEN** an authenticated user selects “使用说明”
- **THEN** the application opens the guide index with current content version and chapter navigation

### Requirement: Guide covers the full user journey
The guide SHALL include quick start, WeChat account, library, interview preparation, Windows/macOS installation, live assistance, screenshot questions, points and membership, points-code redemption, official payment and refund, privacy, FAQ and troubleshooting chapters.

#### Scenario: New user follows quick start
- **WHEN** the user opens the quick-start chapter
- **THEN** the chapter links in order to account, materials, device, interview and billing instructions

#### Scenario: User needs redemption help
- **WHEN** the user searches for an unavailable or already-used points code
- **THEN** the guide explains safe retry, rate limits and customer-service escalation without asking the user to publish the full code

### Requirement: Business pages link to contextual guide chapters
Library, device, billing, preparation and live-workspace pages SHALL provide a help action targeting a stable guide anchor relevant to the current task.

#### Scenario: User needs Windows installation help
- **WHEN** the user selects help from the Windows download area
- **THEN** the guide opens at the Windows installation and troubleshooting anchor

### Requirement: Guide content is versioned and safely rendered
Guide source SHALL be version-controlled structured content or Markdown rendered through an allowlist. Raw scripts, untrusted iframe content and unsafe links MUST be rejected. Stable anchors SHALL remain compatible or redirect after content reorganization.

#### Scenario: Guide Markdown contains a script
- **WHEN** the content pipeline encounters script or disallowed embedded content
- **THEN** the build or publication fails without delivering the unsafe guide

### Requirement: Guide supports discovery and recovery
The guide SHALL provide searchable titles and keywords, previous/next navigation and escalation to configured customer service or customer group when self-service steps do not resolve the issue.

#### Scenario: User searches for payment not received
- **WHEN** the user searches the guide for a delayed payment
- **THEN** the results include official payment status, delayed notification recovery and customer-service escalation steps
