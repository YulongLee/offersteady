## ADDED Requirements

### Requirement: Uploaded material names are distinguishable
The system SHALL provide a non-empty, distinguishable display name for every active material owned by a user while preserving the original filename separately.

#### Scenario: A duplicate filename is uploaded
- **WHEN** a user uploads a material whose candidate display name already exists for the same material type
- **THEN** the system stores a display name with a stable numeric suffix before the file extension
- **AND** the original filename remains unchanged for download

#### Scenario: Historical duplicate names are listed
- **WHEN** existing active materials contain duplicate display names
- **THEN** the material list returns stable, distinguishable display labels for each item

### Requirement: Material display names can be changed
The system SHALL allow an authenticated owner to persistently rename an undeleted resume, job description, or knowledge material without changing the original file.

#### Scenario: Owner renames a material
- **WHEN** the owner submits a valid non-empty display name
- **THEN** the new unique display name is persisted and appears in subsequent material and interview-preparation lists

#### Scenario: Another user attempts to rename a material
- **WHEN** a user submits a rename request for a material owned by another account
- **THEN** the system rejects the request without changing the material

### Requirement: Owners can download original materials
The system SHALL allow an authenticated owner to download the original bytes of an undeleted material without exposing its private object-storage key.

#### Scenario: Owner downloads an available original file
- **WHEN** the owner requests download of an undeleted material whose original object exists
- **THEN** the system returns an attachment with the original bytes, original filename, and stored content type

#### Scenario: Another user requests the download
- **WHEN** a user requests a material owned by another account
- **THEN** the system rejects the request and does not reveal the object key or file contents

#### Scenario: Deleted material is requested
- **WHEN** the owner requests download of a deleted material
- **THEN** the system rejects the request and returns no file contents

### Requirement: Download controls do not change interview material selection
The web application SHALL provide download controls in material management and interview preparation while keeping download interaction independent from selection interaction.

#### Scenario: Download from interview preparation
- **WHEN** a user activates the download control on a selectable material row
- **THEN** the browser downloads that material
- **AND** the row's selected state remains unchanged
