## ADDED Requirements

### Requirement: Global material proxy uploads honor the Backend file limit
The Global Web gateway SHALL forward supported material proxy uploads whose file payload is no larger than the Backend-owned 20 MB limit.

#### Scenario: A PDF larger than the Nginx default uses proxy fallback
- **WHEN** direct object-storage upload fails and a valid PDF larger than 1 MB is sent to a supported proxy route
- **THEN** the Global gateway forwards the request instead of returning HTTP 413

### Requirement: The Global allowance is route-scoped
The Global Web gateway MUST NOT apply the larger material-upload request allowance to unrelated API routes.

#### Scenario: An unrelated API receives a large body
- **WHEN** a body larger than the default gateway limit targets an unrelated API
- **THEN** the material-upload exception does not apply

### Requirement: Global upload errors are accurate and English
The Global Web client SHALL distinguish upload failures from parser failures and SHALL present HTTP 413 as an English file-size validation error.

#### Scenario: Proxy upload is too large
- **WHEN** the proxy returns HTTP 413 before document creation
- **THEN** the user is told to choose a file no larger than 20 MB and the optimistic item is labelled Upload failed
