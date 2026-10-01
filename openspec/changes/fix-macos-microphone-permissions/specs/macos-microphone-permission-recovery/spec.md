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

### Requirement: Independent recovery without redesign
The Mac assistant SHALL perform authorization and status refresh without adding a visible panel or extra buttons. It SHALL preserve the original layout and stylesheet. Startup, focus/visibility refresh and the existing microphone selector SHALL allow permission checks independently of server registration. These operations MUST NOT create a new device identity or record audio for diagnostics. Denied or restricted access SHALL remain recoverable through the operating system's settings, with guidance in the existing control's tooltip.

#### Scenario: First launch while backend is unavailable
- **WHEN** a Mac with undetermined microphone permission opens the assistant and backend registration is unavailable
- **THEN** microphone authorization can proceed independently

#### Scenario: Permission changed in settings
- **WHEN** the user returns to the app after modifying microphone access in system settings
- **THEN** OS status is refreshed and stale earlier requests do not overwrite the newer state

#### Scenario: Permission is restricted
- **WHEN** macOS reports restricted
- **THEN** the existing microphone control's tooltip explains system or administrator restriction rather than repeatedly requesting access

#### Scenario: Preserve the original assistant design
- **WHEN** the assistant is rendered on Mac or Windows after the permission fix
- **THEN** microphone, system audio, screen capture, connection code, footer and existing button positions retain their prior layout, with no additional permission panel or buttons

#### Scenario: Retry without a new control
- **WHEN** a Mac user activates the existing microphone selector after a failed permission check
- **THEN** the assistant rechecks OS status and requests consent only if undetermined, while Windows does not run the Mac permission workflow

### Requirement: Existing production behavior preserved
The release MUST preserve the 1.3.2 interview mode, audio routing, billing, answer, device identity and data retention behavior. This Mac repair SHALL update CN Mac package entries only unless an accompanying Windows release is explicitly approved separately; international releases MUST remain unchanged.

#### Scenario: Release the hotfix
- **WHEN** the CN Mac 1.3.3 artifacts and download entries are published
- **THEN** existing interviews are not forcibly interrupted and no backend business implementation is redeployed

### Requirement: Repackage the original-design correction without publishing
The approved layout correction SHALL be packaged as version 1.3.4 for both Mac architectures, with actual signature, entitlement, architecture and notarization checks. Existing 1.3.3 artifacts MUST remain recoverable. Packaging MUST NOT update production manifests or restart services.

#### Scenario: Repackage for user acceptance
- **WHEN** the user requests new packages after restoration of the original design
- **THEN** both local 1.3.4 DMGs contain the restored layout and retained permission fix, and are delivered with honest validation status without changing online downloads

### Requirement: Approved original-design publication
On subsequent explicit online-update authorization, the publisher SHALL activate the validated CN 1.3.4 Mac packages and accompanying independently approved Windows package using one complete manifest. It MUST verify full remote artifact hashes, retain previous manifests/artifacts, preserve international releases and switch only when no interview is live. Runtime download metadata SHALL be updated without restarting business services.

#### Scenario: Activate the approved 1.3.4 packages
- **WHEN** the user authorizes online update after local packaging validation
- **THEN** public CN downloads report the three approved 1.3.4 packages with correct hashes and honest signing status, while service identity/start time and international artifacts remain unchanged
