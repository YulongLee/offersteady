## ADDED Requirements

### Requirement: Public discovery sources MUST reference the expanded canonical surface
The sitemap, `llms.txt`, `llms-full.txt`, and `public-facts.json` MUST reference the maintained commercial and guide pages using consistent product naming and canonical URLs.

#### Scenario: Verifier compares discovery artifacts
- **WHEN** release verification compares public discovery sources with route documents
- **THEN** every referenced canonical page exists, is indexable, returns success, and does not contradict the maintained product facts

### Requirement: Search-oriented AI crawler access MUST be explicit
robots.txt MUST explicitly allow the maintained search and answer-engine crawlers while preserving the existing general crawl policy and sitemap location. Training-crawler permissions MUST NOT change without a separate approved decision.

#### Scenario: AI crawler reads robots policy
- **WHEN** GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, or PerplexityBot requests robots.txt
- **THEN** the crawler receives an explicit allow rule for public content

### Requirement: Public entity data MUST not infer unresolved identities
Public HTML, JSON-LD, and GEO files MUST use the verified product name and existing contact facts but MUST NOT infer a registered legal operator, individual author, social profile, customer, rating, review, or performance statistic from unrelated configuration or marketing copy.

#### Scenario: Legal operator remains unresolved
- **WHEN** public entity data is generated or updated before legal verification
- **THEN** it omits `legalName` and avoids presenting an SMS signature or team label as the registered operator

### Requirement: Public release checks MUST cover commercial and authority regressions
The deterministic release suite MUST validate the new routes, metadata, H1s, canonicals, structured data, internal links, sitemap entries, crawler rules, GEO references, non-affiliation language, and mutable-state boundaries.

#### Scenario: A commercial page embeds stale mutable state
- **WHEN** a static decision page includes an exact release artifact or an unapproved price assertion outside the documented public contract
- **THEN** the release check fails before deployment and identifies the offending page
