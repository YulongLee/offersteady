## ADDED Requirements

### Requirement: Uploaded materials become backend capabilities asynchronously
The system SHALL treat material upload completion as the start of an asynchronous backend processing pipeline that produces reusable interview capabilities. The pipeline MUST save the original object, normalized Markdown, chunk artifacts, vector index metadata and safe status records without requiring the user to stay on the upload dialog.

#### Scenario: User uploads a supported document
- **WHEN** a user uploads a PDF, DOCX, DOC, TXT or MD material and the original file is stored in OSS
- **THEN** the backend creates or updates a document version in the database and starts processing without blocking navigation to other product pages

#### Scenario: User leaves the library page during processing
- **WHEN** processing continues after the upload dialog closes or the user navigates away
- **THEN** the backend continues the processing job and later exposes the final ready or failed state through the shared material list

### Requirement: MinerU conversion produces verified Markdown artifacts
The system SHALL convert uploaded materials to normalized Markdown through the configured parser pipeline and MUST store the resulting Markdown as a processed OSS artifact linked to the document version. The system MUST mark the document version failed or retryable when conversion cannot produce readable Markdown.

#### Scenario: MinerU conversion succeeds
- **WHEN** MinerU returns a completed extraction result for a document version
- **THEN** the backend stores `normalized.md` under the processed artifact path and records the artifact as verified for that document version

#### Scenario: MinerU conversion fails
- **WHEN** MinerU returns failure, times out or the converted Markdown is empty
- **THEN** the document version is not selectable for interviews and the material list exposes a safe failure reason

### Requirement: Knowledge materials produce chunks and vector index records
The system SHALL build chunk artifacts and vector index records for Knowledge materials before marking them selectable. Resume and JD materials SHALL be allowed to become selectable after verified normalized Markdown is available, even if they are not used as default RAG sources.

#### Scenario: Knowledge indexing succeeds
- **WHEN** a Knowledge document has verified Markdown and embedding succeeds for its chunks
- **THEN** the backend stores `chunks.jsonl`, writes runtime vector chunks and marks the document version as indexed and selectable

#### Scenario: Knowledge indexing is incomplete
- **WHEN** a Knowledge document has Markdown but no vector chunks are available
- **THEN** the document remains visible as processing or failed but MUST NOT be selectable as a Knowledge source for a new interview

#### Scenario: Resume Markdown is available
- **WHEN** a Resume document has verified normalized Markdown
- **THEN** the document can become selectable as fixed interview context without requiring Knowledge RAG retrieval to succeed

### Requirement: Material selectable state is derived from database records
The system SHALL expose a material as selectable only when the database records show that the current document version is owned by the user, not deleted, not disabled, processed to the required artifact level for its kind and ready for its intended use. The client MUST NOT infer selectability from file names, OSS paths or local state.

#### Scenario: Ready material appears in the library
- **WHEN** a document version satisfies the selectable rules for its kind
- **THEN** the library and preparation pages both show it as available for interview selection with the same document ID and version ID

#### Scenario: Material is not selectable
- **WHEN** a document version is processing, failed, deleted, disabled or missing required artifacts
- **THEN** the backend marks it unselectable and provides a safe unavailable reason for product UI

### Requirement: Frontend material lists are synchronized through the backend
The system SHALL render library and preparation material lists from backend material records rather than direct OSS bucket listing or browser-local state. The backend material record MUST be the user-facing source of truth, while OSS stores the referenced artifacts that the backend verifies and reconciles.

#### Scenario: Material exists in OSS and database
- **WHEN** a material document has database records and verified OSS artifacts
- **THEN** the frontend displays the material with the backend status, version and selectable state

#### Scenario: Material exists in OSS but not database
- **WHEN** an object is present in OSS without a corresponding backend material record for the current user
- **THEN** the frontend does not automatically display it as a usable material unless a backend reconciliation process imports or links it safely

#### Scenario: Material exists in database but OSS artifacts are missing
- **WHEN** the backend detects that required OSS artifacts for a document version are missing
- **THEN** the material becomes stale or unselectable and the frontend shows the backend-provided safe reason

### Requirement: Material creation and deletion synchronize database, OSS and vector records
The system SHALL coordinate material creation and deletion across database records, OSS objects and vector records. Creation MUST not mark a material selectable until required artifacts exist. Deletion MUST remove the material from future selection immediately and schedule cleanup of OSS artifacts and vector chunks.

#### Scenario: New material is uploaded
- **WHEN** the user completes an upload through a backend-issued upload intent
- **THEN** the backend records the document version, verifies the OSS original object and starts processing before exposing it as ready or selectable

#### Scenario: User deletes a material
- **WHEN** the user deletes a material from the library
- **THEN** the backend marks the document deleted and unselectable immediately, removes it from frontend selectable lists, and schedules OSS and vector cleanup

#### Scenario: OSS cleanup fails after deletion
- **WHEN** the database delete marker is saved but OSS artifact cleanup fails
- **THEN** the frontend continues to treat the material as deleted while the backend keeps a retryable cleanup job

### Requirement: OSS artifact checks happen outside the interview binding critical path
The system SHALL perform required OSS artifact existence and readability checks during material processing and optional background reconciliation. Confirming materials for an interview MUST NOT synchronously re-run MinerU, rebuild embeddings or perform broad OSS scans.

#### Scenario: User confirms materials for an interview
- **WHEN** the selected document versions are already marked selectable in the database
- **THEN** the confirmation path completes using lightweight database validation rather than synchronous OSS conversion or indexing

#### Scenario: Background reconciliation finds missing artifacts
- **WHEN** a later backend check detects that a previously verified processed artifact is missing
- **THEN** the affected document version becomes stale or unselectable for future confirmations without silently modifying existing answer history
