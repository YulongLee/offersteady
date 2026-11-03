## ADDED Requirements

### Requirement: Separate immutable regional source seal
After successful Global acceptance the release SHALL push authorized current development and independent exact CN/Global public runtime snapshots with hashes and restoration instructions, without private data or forcing existing refs.

#### Scenario: Offline restoration
- **WHEN** either regional component is restored into a new offline directory
- **THEN** all archived public bytes match its actual verified runtime manifest and CN code is not substituted for Global

#### Scenario: Publish Git version
- **WHEN** scope/privacy/link/spec/snapshot checks pass and the chosen version does not exist remotely
- **THEN** a normal commit and immutable tag are pushed and their actual remote identities are verified
