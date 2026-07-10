## ADDED Requirements

### Requirement: User can manage knowledge collections and documents
An authenticated user SHALL be able to create and rename a knowledge collection, add supported documents, inspect document status and delete documents or collections they own. Creating an empty collection SHALL NOT create a billable usage.

#### Scenario: User creates an empty collection
- **WHEN** a user submits a valid unique collection name
- **THEN** the system creates the collection for that user and does not reserve or deduct points

#### Scenario: User uploads a supported document
- **WHEN** the user adds an allowed PDF, DOCX, TXT or Markdown file within configured limits
- **THEN** the system creates a document version in a pending state and presents the indexing estimate before billable processing

#### Scenario: User attempts to manage another user's collection
- **WHEN** a request targets a collection or document owned by another user
- **THEN** the system rejects the request without exposing names, contents or processing metadata

### Requirement: Document lifecycle exposes truthful processing states
Documents SHALL expose pending, processing, ready, failed, disabled and deleted states. Only a ready, non-disabled version SHALL be eligible for a new interview selection or retrieval operation.

#### Scenario: Document parsing fails
- **WHEN** parsing or indexing fails before a usable index is delivered
- **THEN** the document enters failed state, the reserved points are released and the UI provides replace, retry or delete actions

#### Scenario: Document is still processing
- **WHEN** a user prepares an interview while a selected document is processing
- **THEN** the document is visibly unavailable and the system does not silently substitute another source

### Requirement: Deletion immediately removes future retrieval access
Deleting a document or collection SHALL immediately invalidate its use in future retrieval and SHALL schedule stored content and derived index data for deletion. Historical answers MAY retain only a minimal source label, version and deleted marker.

#### Scenario: Selected document is deleted
- **WHEN** a user confirms deletion of a document selected by an interview
- **THEN** future questions cannot retrieve it, the interview selection requires attention and no replacement is selected automatically

#### Scenario: User reviews an old answer after source deletion
- **WHEN** an old answer referenced the deleted source
- **THEN** the answer displays its minimal historical source label and deleted status without restoring document content

### Requirement: Destructive library actions require explicit confirmation
The interface SHALL explain the affected documents, current interview selections and deletion scope before deleting a non-empty collection. Repeated delete requests MUST be idempotent.

#### Scenario: User cancels collection deletion
- **WHEN** the user opens the delete confirmation and cancels
- **THEN** the collection, documents, selections and indexes remain unchanged

