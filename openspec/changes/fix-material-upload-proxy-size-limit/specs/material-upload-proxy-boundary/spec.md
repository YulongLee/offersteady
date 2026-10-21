## ADDED Requirements

### Requirement: Material proxy uploads honor the product file limit
The Chinese production Web gateway SHALL accept multipart proxy uploads for resume, job-description, and knowledge material files whose file payload does not exceed the Backend-owned 20 MB limit.

#### Scenario: PDF larger than the Nginx default is uploaded
- **WHEN** a user uploads a valid 1.66 MB PDF and direct OSS upload falls back to a supported material proxy route
- **THEN** the gateway forwards the request to the Backend instead of returning HTTP 413

#### Scenario: Backend retains the authoritative file limit
- **WHEN** a proxy upload contains a file larger than the product's 20 MB limit
- **THEN** the Backend rejects it using the existing material validation without beginning parsing

### Requirement: The larger gateway allowance is route-scoped
The Web gateway MUST limit the larger request-body allowance to the resume, job-description, and knowledge-material proxy upload routes and MUST NOT apply it to unrelated API routes.

#### Scenario: An unrelated API receives a large request
- **WHEN** a request larger than the default gateway allowance targets an unrelated `/api/` endpoint
- **THEN** the material-upload exception does not apply

### Requirement: Upload and parsing failures remain distinguishable
The Web client SHALL describe a failure before document registration as an upload failure and SHALL NOT identify it as a PDF parser failure.

#### Scenario: Gateway rejects the upload
- **WHEN** the proxy upload returns HTTP 413 before a document and processing task are created
- **THEN** the user sees an upload-size failure and no optimistic item is labelled as a parser failure

### Requirement: Production follow-up is derived from the active component baseline
For the explicitly authorized 2026-10-21 gateway-only follow-up, the release SHALL derive its Nginx candidate from the actual active Chinese Web component's pinned configuration bytes and SHALL preserve all pre-existing bytes outside one material-proxy location insertion. It SHALL NOT treat the repository config, a prior completed release task, or a historical image tag as proof of the active gateway boundary.

#### Scenario: Active gateway has regressed to the default body allowance
- **WHEN** the actual pinned gateway config contains no material proxy body allowance even though the repository config contains it
- **THEN** the candidate inserts only the route-scoped 21MiB request envelope before the existing generic API location and retains the application's 20MiB file limit

#### Scenario: Baseline or routing conflicts differ from the approved input
- **WHEN** the config SHA changes, a competing upload location exists, or a higher-priority location can shadow the targeted routes
- **THEN** candidate preparation fails without mutating the input or overwriting unrelated configuration

#### Scenario: Existing user flows remain byte-identical
- **WHEN** the gateway candidate is prepared
- **THEN** removing the single inserted block restores the exact original config bytes, including existing CSP, SSE, static assets, simulated-interview and other application routes

### Requirement: Current gateway follow-up has independent truthful verification
The 2026-10-21 release SHALL prove the gateway boundary in an isolated environment using synthetic bytes and a side-effect-free upstream, and SHALL report the current frontend upload-error wording limitation separately. Historical frontend-error tasks SHALL NOT be counted as a frontend modification in this gateway-only follow-up.

#### Scenario: A maximum-size file is tested without production document creation
- **WHEN** a synthetic file of exactly 20 × 1024 × 1024 bytes is sent with multipart metadata through each isolated material proxy route
- **THEN** each request reaches the synthetic upstream without HTTP413, and no production document, parser task, billing operation or user record is created

#### Scenario: Envelope and product payload boundaries differ
- **WHEN** a request envelope exceeds 21MiB or an unrelated endpoint receives a 1.5MiB request
- **THEN** the isolated gateway returns HTTP413, while a separate Backend validation regression proves a 20MiB file is allowed and a 20MiB-plus-one-byte file is rejected

#### Scenario: Frontend JavaScript is outside this follow-up
- **WHEN** the gateway follow-up is deployed
- **THEN** all frontend JavaScript assets remain identical and the release explicitly states that the generic failed/"解析失败" wording has not been changed in this follow-up
