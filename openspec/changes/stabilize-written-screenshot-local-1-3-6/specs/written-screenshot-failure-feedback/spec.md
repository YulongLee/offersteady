## ADDED Requirements

### Requirement: Show concise stage specific written failures
The existing written screenshot error UI SHALL distinguish assistant offline or invalid binding, capture failure and upload failure using existing server contracts. It SHALL preserve the approved layout, avoid persistent declarations or new recheck controls, retain valid pending images and fence obsolete cancellation callbacks.

#### Scenario: The webpage is online but the companion is unavailable
- **WHEN** written screenshot admission reports desktop offline or invalid binding
- **THEN** the existing error entry directs the user to restore the companion connection without presenting the failure as model generation

#### Scenario: A cancelled old request reports an error
- **WHEN** an obsolete request fails after the user has started a new one
- **THEN** its callback cannot replace the new task or its error state

### Requirement: Deliver a same version local candidate
The change SHALL retain version 1.3.6, the r2 appearance, permission/audio fixes, transparent clickable Tray and domestic identity/default endpoints. It SHALL provide verified local Mac arm64/x64 and Windows x64 packages without updating production, official manifests, OSS or Git remotes. Validation SHALL use synthetic inputs only and clearly record physical device limits.

#### Scenario: Local validation finishes
- **WHEN** the revised candidate is handed off
- **THEN** exact source/payload checks and regression results accompany local installers and no production or distribution mutation has occurred
