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
