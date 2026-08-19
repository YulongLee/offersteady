## ADDED Requirements

### Requirement: Public topic pages MUST represent distinct existing user intents
The site MUST publish a curated set of public Chinese pages that each address one distinct existing product capability or setup problem. Every page MUST contain unique server-delivered content and MUST NOT claim capabilities, integrations, customers, outcomes, or accuracy that cannot be verified from the current product.

#### Scenario: Crawler requests a topic page without JavaScript
- **WHEN** a crawler requests any sitemap-listed topic URL without executing JavaScript
- **THEN** it receives a successful HTML response with a unique title, description, H1, substantive topic content, and truthful product boundary

### Requirement: Public topic pages MUST be canonical and discoverable
Every topic page MUST use an absolute self-canonical URL, MUST be linked from at least one other public page with an ordinary anchor, and MUST link to relevant canonical public pages such as the homepage, guide, or another topic page.

#### Scenario: Crawler traverses the topic cluster
- **WHEN** a crawler starts from the homepage or guide and follows ordinary links
- **THEN** it can discover every sitemap-listed topic page without relying on JavaScript or form submission

### Requirement: Public topic pages MUST preserve product boundaries
Topic content MUST describe AI output as assistive suggestions, MUST require users to rely on truthful personal experience, and MUST avoid encouraging unauthorized recording, covert use, or violation of interview and meeting-platform rules.

#### Scenario: Visitor reads capability guidance
- **WHEN** a visitor reads a topic page about realtime, screenshot, or review assistance
- **THEN** the page explains the user-controlled workflow and relevant limitations without presenting the product as a guaranteed or deceptive substitute for the user

### Requirement: Sitemap membership MUST reflect maintained public content
The sitemap MUST list only successful, indexable, self-canonical public topic URLs and MUST include an accurate maintained `lastmod` value for each listed document.

#### Scenario: A public topic document changes
- **WHEN** a topic page receives a material content update
- **THEN** its sitemap `lastmod` value is updated to the release date while unrelated pages retain their own dates
