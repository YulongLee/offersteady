## ADDED Requirements

### Requirement: Public product images use a managed directory structure
The Web project SHALL organize public images under brand, payments and support asset directories. Components SHALL reference stable asset IDs or controlled public configuration instead of scattering raw paths.

#### Scenario: Developer adds a product logo
- **WHEN** a new logo variant is introduced
- **THEN** it is stored under the brand directory and registered with purpose, dimensions, alternative text, version and content hash

### Requirement: Asset manifest validates public usage
Every published asset SHALL have a manifest entry containing stable ID, relative path or controlled URL, purpose, accessibility text, version, integrity metadata, public state and optional expiry. Missing, expired or integrity-failed assets SHALL use a safe fallback.

#### Scenario: Customer-group QR expires
- **WHEN** the support asset expiry passes
- **THEN** the page stops showing the expired image and falls back to current customer-service contact information

### Requirement: Sensitive operational images remain replaceable
Production customer-service and customer-group QR images SHALL be replaceable through authorized configuration or object storage without requiring a Web deployment. Repository fixtures MUST be synthetic and MUST NOT contain private account or production collection information.

#### Scenario: Operations replaces the customer-service QR
- **WHEN** an authorized operator publishes a new verified support asset
- **THEN** clients receive the new version and the previous version is withdrawn with an audit record

### Requirement: Official payment QR values are not static assets
Order-specific WeChat Pay and Alipay QR values SHALL be rendered from short-lived official provider checkout results and MUST NOT be committed to the public assets directory.

#### Scenario: Checkout renders a payment QR
- **WHEN** an official provider returns a valid order QR value
- **THEN** the UI renders it for that order and does not resolve it through the static asset manifest

