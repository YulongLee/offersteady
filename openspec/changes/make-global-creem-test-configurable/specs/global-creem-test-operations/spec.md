## ADDED Requirements

### Requirement: Operators can configure Creem environments safely
The Global Admin SHALL allow an authorized operator to replace Test or Live API credentials while storing them only as server-encrypted ciphertext and returning only configured state and a non-reversible fingerprint. Test and Live credentials MUST remain isolated, and any credential change MUST disable new checkout for that environment pending validation.

#### Scenario: Operator saves Test credentials
- **WHEN** an authorized operator submits a Test API key and Test Webhook Secret
- **THEN** the Backend encrypts them at rest, returns no secret value, leaves Live configuration unchanged, and disables Test checkout until the remaining gates pass

#### Scenario: Operator reads saved configuration
- **WHEN** the Global Admin reloads after credentials were saved
- **THEN** it receives configured flags and fingerprints without receiving API keys, Webhook Secrets, or ciphertext

### Requirement: Operators can discover Creem products
The Global Backend SHALL use the selected environment's server-side API key to retrieve a bounded Creem product catalogue and SHALL return only safe product metadata required for mapping.

#### Scenario: Test connection succeeds
- **WHEN** the operator requests Test product synchronization with a valid Test API key
- **THEN** the Admin receives provider product name, identifier, price, currency, billing type, billing period, status, and Test mode without receiving credentials

#### Scenario: Provider connection fails
- **WHEN** the API key is invalid, belongs to the wrong environment, the provider is unavailable, or the response is invalid
- **THEN** the Admin shows a safe actionable failure and checkout remains disabled

### Requirement: Paid plans map through readable validated choices
The Global Admin SHALL show the four paid OfferSteady plans using customer-facing names and commercial terms and SHALL map them to synchronized Creem products through a selector. Free MUST be identified as not requiring a Creem product. The Backend MUST freshly validate environment, active status, amount, currency, billing mode, and current plan version before marking a mapping ready.

#### Scenario: Matching Test product is selected
- **WHEN** an operator maps a paid OfferSteady plan to an active Test product with matching USD amount and billing mode
- **THEN** the Test mapping is stored as ready, its safe provider metadata is shown, and Test checkout remains disabled until explicit activation

#### Scenario: Product facts do not match
- **WHEN** a selected product is inactive, belongs to Live, has a different price or currency, or has a different billing type
- **THEN** the mapping is rejected with field-specific guidance and cannot satisfy activation readiness

### Requirement: Test activation cannot affect Live commerce
Test and Live catalogues, mappings, activation state, and acceptance diagnostics MUST remain independent. The deployment-selected environment SHALL remain authoritative for customer checkout, and switching to Live SHALL require separately configured and validated Live credentials and products.

#### Scenario: Test checkout is activated
- **WHEN** all Test readiness gates pass and an authorized operator explicitly activates Test checkout while the deployment is in Test mode
- **THEN** customer checkout uses the Creem Test API and Test products only and cannot create a real charge

#### Scenario: Merchant approval is later completed
- **WHEN** the operator prepares Live credentials and products after approval
- **THEN** existing Test configuration remains unchanged and Live cannot serve customer checkout until the deployment mode is switched and Live is explicitly activated

### Requirement: Existing product paths remain isolated
The change SHALL NOT add Creem configuration or provider calls to Chinese-edition routes or to interview, Companion, ASR, RAG, AI, authentication, and ordinary API request paths.

#### Scenario: Global Creem administration is released
- **WHEN** regression tests run against Chinese and Global editions
- **THEN** Chinese commerce behavior and both editions' core interview behavior remain unchanged
