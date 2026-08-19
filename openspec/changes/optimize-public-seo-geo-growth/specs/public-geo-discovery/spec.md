## ADDED Requirements

### Requirement: The site MUST publish canonical AI discovery artifacts
The site MUST publish `llms.txt`, `llms-full.txt`, and a machine-readable public fact document that identify the canonical site, product purpose, primary public pages, product boundaries, privacy references, and contact route.

#### Scenario: Answer engine requests the concise discovery file
- **WHEN** a client requests `/llms.txt`
- **THEN** it receives plain text with the canonical product description and links to maintained public sources

#### Scenario: Answer engine requests detailed public facts
- **WHEN** a client requests `/llms-full.txt` or `/public-facts.json`
- **THEN** it receives factual, versioned public information without user data, secrets, unverifiable claims, or authenticated content

### Requirement: Structured entities MUST remain consistent across public sources
Public HTML, JSON-LD, AI discovery files, sitemap URLs, and visible brand copy MUST use consistent canonical URLs and product naming. Legal entity data MUST NOT be added until the registered operator is verified.

#### Scenario: Verifier compares public entity sources
- **WHEN** the release verifier parses homepage, guide, topic pages, and GEO artifacts
- **THEN** product name, canonical host, guide URL, privacy URL, terms URL, and contact information do not contradict one another

### Requirement: GEO content MUST distinguish product facts from guidance
AI discovery artifacts MUST clearly separate verified product capabilities, user responsibilities, and non-guaranteed AI guidance. They MUST NOT expose prompts, internal model configuration, personal data, payment credentials, or private API routes.

#### Scenario: Public fact source is inspected for sensitive data
- **WHEN** the release verifier scans the GEO artifacts
- **THEN** it finds only approved public facts and no secret-like values, personal test data, internal prompts, or private endpoints
