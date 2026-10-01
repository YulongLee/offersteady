## ADDED Requirements

### Requirement: Signed audio input access
Mac release app and audio helper executables SHALL have audio-input entitlement enabled alongside Hardened Runtime and microphone usage descriptions. Release validation MUST reject missing or false entitlements.

#### Scenario: Inspect a signed Mac release
- **WHEN** either arm64 or x64 is prepared for release
- **THEN** actual signed app and helper entitlements are checked and a missing or false audio-input entitlement prevents publication

### Requirement: Consent has no artificial deadline
The assistant SHALL distinguish checking, pending, granted, denied, restricted, not-determined and error states. It MUST NOT classify a user who has not answered the OS prompt as denied.

#### Scenario: User allows after ten seconds
- **WHEN** an OS permission prompt remains unanswered for ten seconds and the user subsequently allows access
- **THEN** the assistant remains pending until completion and then reports granted

#### Scenario: Duplicate requests
- **WHEN** two callers request permission while an OS request is pending
- **THEN** only one OS request is active and callers receive its actual result

#### Scenario: OS request fails
- **WHEN** permission IPC fails without an OS denial
- **THEN** the UI shows a recoverable check error rather than claiming user denial

### Requirement: Visible independent recovery
The Mac assistant SHALL expose a permission panel with authorization, status refresh and microphone settings navigation. These operations MUST NOT depend on server registration, create a new device identity or record audio for diagnostics.

#### Scenario: First launch while backend is unavailable
- **WHEN** a Mac with undetermined microphone permission opens the assistant and backend registration is unavailable
- **THEN** microphone authorization can proceed independently

#### Scenario: Permission changed in settings
- **WHEN** the user returns to the app after modifying microphone access in system settings
- **THEN** OS status is refreshed and stale earlier requests do not overwrite the newer state

#### Scenario: Permission is restricted
- **WHEN** macOS reports restricted
- **THEN** the panel explains system or administrator restriction rather than repeatedly requesting access

### Requirement: Existing production behavior preserved
The release MUST preserve the 1.3.2 interview mode, audio routing, billing, answer, device identity and data retention behavior. Only CN Mac package entries SHALL be updated; Windows and international releases MUST remain unchanged.

#### Scenario: Release the hotfix
- **WHEN** the CN Mac 1.3.3 artifacts and download entries are published
- **THEN** existing interviews are not forcibly interrupted and no backend business implementation is redeployed
