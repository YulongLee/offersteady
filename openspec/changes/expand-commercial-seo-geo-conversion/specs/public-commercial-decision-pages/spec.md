## ADDED Requirements

### Requirement: Public visitors MUST be able to evaluate stable commercial facts without authentication
The site MUST publish server-delivered pricing, download, security, product identity, and contact pages that explain the stable decision information available to unauthenticated visitors and link to the authoritative product surface for mutable state.

#### Scenario: Visitor evaluates pricing before login
- **WHEN** a visitor requests the public pricing page without JavaScript or an authenticated session
- **THEN** the response explains points and membership choices, charging boundaries, and payment confirmation while directing current catalog prices to the authoritative billing surface

#### Scenario: Visitor evaluates desktop availability
- **WHEN** a visitor requests the public download page
- **THEN** the response explains supported desktop families, architecture and permission considerations, and directs current versions and artifacts to the authoritative download center without embedding stale release data

### Requirement: Commercial decision pages MUST remain truthful and privacy-safe
Public commercial pages MUST NOT expose private APIs, credentials, user data, internal prompts, mutable backend state, unverified legal entities, fabricated customers, guaranteed outcomes, or unsupported product claims.

#### Scenario: Release verification scans decision pages
- **WHEN** the public release verifier inspects the five commercial decision documents
- **THEN** it finds only approved public facts, canonical public links, and explicit boundaries for dynamic or sensitive information

### Requirement: Commercial decision pages MUST be indexable and discoverable
Each decision page MUST have unique server-delivered content, one H1, route-specific metadata, a self-canonical URL, crawlable internal links, valid JSON-LD, sitemap membership, and an explicit production route mapping.

#### Scenario: Crawler traverses commercial pages
- **WHEN** a crawler starts from the homepage, guide, or another public page
- **THEN** it can discover each commercial decision page and receive HTTP 200 without executing JavaScript
