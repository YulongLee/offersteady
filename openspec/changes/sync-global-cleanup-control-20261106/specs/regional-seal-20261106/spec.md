## ADDED Requirements

### Requirement: Publish an immutable regional source seal after deployment
After verified deployment, the seal MUST bind current CN/Global public runtime sources for all six components, exact manifests, recovery tools, approved development changes and sanitized evidence. Private configuration/keys/user data/raw logs MUST NOT enter Git. A fresh codex branch, normal commit and immutable new tag MUST be pushed and remotely verified without force or moving old tags.

#### Scenario: Seal and verify remote ownership
- **WHEN** six actual component sources, tests, links and privacy checks pass
- **THEN** commit and push the reviewed scope with release-20261106.1 or the next unused version, verify exact remote commit/tag ownership and document regional production versus unreleased development boundaries
