## ADDED Requirements

### Requirement: Material uploads are stored in OSS with database metadata
The system SHALL store uploaded Resume, JD and Knowledge documents in Aliyun OSS and register each upload in PostgreSQL with owner user ID, document kind, display name, file metadata, object key, content fingerprint, version, lifecycle status and audit timestamps.

#### Scenario: User uploads a supported material file
- **WHEN** an authenticated user uploads a supported PDF, DOCX, DOC, TXT or MD file through the material library
- **THEN** the system stores the object in OSS under a generated non-guessable key and persists a document version record owned by that user

#### Scenario: User uploads two files with the same name
- **WHEN** the same user uploads two different files with the same original filename
- **THEN** the system preserves both versions with distinct document/version/object identifiers and MUST NOT overwrite the prior OSS object

#### Scenario: Browser inspects upload response
- **WHEN** the browser receives the upload intent or completion response
- **THEN** the response MUST NOT contain OSS access keys, database credentials or server-side provider secrets

### Requirement: OSS object keys are environment-scoped and privacy-preserving
The system SHALL generate OSS object keys that include configured prefix and environment, separate document kind and version, and avoid raw filenames, email addresses, provider subject identifiers or other directly identifying user data.

#### Scenario: Object key is generated for original material
- **WHEN** the backend creates an OSS key for a material upload
- **THEN** the key follows the approved documents path shape and uses server-generated opaque IDs instead of user-provided names

#### Scenario: Processed artifacts are stored
- **WHEN** normalized Markdown or chunk artifacts are written for a document version
- **THEN** they are stored below the same document version prefix in a processed artifact path

### Requirement: Material lifecycle supports delete and cleanup without future retrieval
The system SHALL support soft deletion for documents and collections, immediately prevent deleted or disabled versions from future selection and retrieval, and schedule raw objects, processed artifacts and vector entries for cleanup while preserving minimal audit metadata.

#### Scenario: User deletes a document
- **WHEN** a user confirms deletion of a material document
- **THEN** the document version becomes unavailable for future interview selection and retrieval before asynchronous object/vector cleanup completes

#### Scenario: User reviews historical answer after deletion
- **WHEN** an old answer referenced a deleted document version
- **THEN** the answer shows only source name, source kind, version and deleted marker without restoring document content

### Requirement: Material access is owner-scoped
The system SHALL enforce owner-scoped access for upload intents, metadata reads, replacement, deletion, processing status and download or preview operations.

#### Scenario: User requests another user's document
- **WHEN** a request targets a document, version, collection, object or processing job owned by another user
- **THEN** the system rejects the request without exposing names, object keys, processing metadata or content fingerprints
