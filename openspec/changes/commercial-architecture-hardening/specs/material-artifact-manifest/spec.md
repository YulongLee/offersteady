## ADDED Requirements

### Requirement: Material versions have explicit artifact manifests
The system SHALL maintain artifact manifest records for each material document version. Each artifact record MUST include artifact kind, object key, sync status, and verification time when available.

#### Scenario: Original upload is confirmed
- **WHEN** the backend confirms that the original upload object exists in OSS
- **THEN** it records an `original` artifact for the document version

#### Scenario: Markdown conversion succeeds
- **WHEN** normalized Markdown is saved to OSS
- **THEN** the backend records a `normalized_markdown` artifact with synced status

#### Scenario: Chunk manifest is produced
- **WHEN** chunks.jsonl is saved to OSS
- **THEN** the backend records a `chunk_manifest` artifact linked to the same document version

### Requirement: Selectability depends on required artifacts
The system SHALL mark a document version selectable only when required artifacts for its material kind are present and synced. Knowledge materials MUST require vector-ready chunk artifacts; Resume and JD materials MUST require normalized Markdown.

#### Scenario: Knowledge chunks are missing
- **WHEN** a Knowledge document version has no synced chunk manifest or vector chunks
- **THEN** it is not selectable for interview confirmation

#### Scenario: Resume Markdown is missing
- **WHEN** a Resume document version lacks synced normalized Markdown
- **THEN** it is not selectable as fixed interview context

### Requirement: Deleted materials remain hidden while cleanup continues
The system SHALL mark deleted materials unselectable immediately, even when OSS or vector cleanup is still pending.

#### Scenario: OSS cleanup is pending
- **WHEN** a material has been deleted in the database but cleanup jobs are still queued
- **THEN** frontend material lists do not show it as selectable or ready
