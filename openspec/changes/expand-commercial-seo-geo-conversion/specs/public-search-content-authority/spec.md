## ADDED Requirements

### Requirement: High-intent guides MUST answer distinct user questions with substantive content
The site MUST publish a curated guide cluster for macOS permissions, Feishu audio setup, Tencent Meeting audio setup, and STAR interview-answer structure. Each guide MUST give a direct answer, practical steps, limitations, and related canonical resources without duplicating another page's primary intent.

#### Scenario: Visitor opens a platform setup guide
- **WHEN** a visitor opens a Feishu or Tencent Meeting audio guide
- **THEN** the page distinguishes microphone, computer output, operating-system permission, and meeting-platform settings without implying official partnership or guaranteed capture

#### Scenario: Visitor opens the STAR answer guide
- **WHEN** a visitor opens the STAR interview-answer guide
- **THEN** the page explains how to organize truthful personal experience and does not invent candidate achievements or present AI output as a standard answer

### Requirement: Guide ownership and freshness MUST be visible and machine-readable
Every new guide and the maintained core guides MUST show an organization-level reviewer, published or reviewed date, modified date, source boundary, and Article-compatible JSON-LD alongside BreadcrumbList data.

#### Scenario: Crawler parses a guide
- **WHEN** a crawler parses any maintained public guide
- **THEN** it can identify the title, canonical URL, organization author or reviewer, publisher, publication or review date, modification date, and breadcrumb path

### Requirement: Content pages MUST support passage-level discovery
Each guide MUST contain question-led headings and at least one self-contained direct-answer passage that can be understood without relying on preceding page context.

#### Scenario: Answer engine extracts a guide passage
- **WHEN** an answer engine selects a section matching a user question
- **THEN** the first sentences provide a complete bounded answer before optional detail or navigation
