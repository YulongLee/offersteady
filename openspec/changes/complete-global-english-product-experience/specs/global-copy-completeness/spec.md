## ADDED Requirements

### Requirement: Explicit English product copy
The Global application SHALL display concise, context-appropriate English for every product-authored label, heading, description, action, validation message, empty state, loading state, and error state on every supported customer route.

#### Scenario: User visits a Global feature route
- **WHEN** a user opens any supported public, authentication, interview, written-exam, material, billing, guide, device, or settings route
- **THEN** all product-authored UI copy is meaningful English for that component and is not a generic category fallback

#### Scenario: User views material management
- **WHEN** a user opens the Global materials page in any supported material state
- **THEN** tabs, counts, upload actions, collection actions, processing states, and empty states describe their actual purpose in English

### Requirement: Missing translations fail verification
The Global build SHALL detect product-authored Chinese literals that lack an explicit approved mapping and SHALL fail copy verification with enough source information to correct them.

#### Scenario: Developer adds an unmapped product literal
- **WHEN** a product-authored Chinese literal is added to Global source without an explicit English mapping
- **THEN** the copy audit or build fails and identifies the missing literal and source location

### Requirement: Runtime content is preserved
The translation system MUST NOT automatically rewrite user-entered content, uploaded material text, transcripts, generated answers, or arbitrary server-provided values merely because they contain Chinese characters.

#### Scenario: User material contains Chinese text
- **WHEN** a Global user views Chinese text originating from their own material or an interview transcript
- **THEN** the source content remains unchanged while surrounding product controls remain English

