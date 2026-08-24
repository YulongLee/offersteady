## ADDED Requirements

### Requirement: Stable production identity
The macOS release SHALL keep bundle identifier `com.offersteady.companion` and SHALL use `Developer ID Application: Yulong li (8Y5FAR3TF3)` without ad-hoc or development-signing fallback.

#### Scenario: Release identity is unavailable
- **WHEN** the exact Developer ID identity is not available in the active keychain
- **THEN** production packaging fails before generating a distributable DMG

### Requirement: Complete hardened signing chain
The macOS release SHALL enable Hardened Runtime and trusted timestamps and SHALL sign the outer app, Electron helper apps, frameworks, dylibs, executables, and native Swift capture runtime with a complete Developer ID chain.

#### Scenario: Nested executable is unsigned
- **WHEN** verification finds an unsigned or differently signed nested Mach-O component
- **THEN** the release fails and is not eligible for website distribution

### Requirement: Minimal capture permissions
The release SHALL retain microphone, screen recording, and system-audio usage descriptions while including only entitlements required by the non-sandboxed Electron runtime.

#### Scenario: Permission metadata is inspected
- **WHEN** the signed app Info.plist and entitlements are inspected
- **THEN** all three capture usage descriptions are present and no unneeded unsigned-executable-memory or App Sandbox entitlement is enabled

### Requirement: Mandatory notarization and stapling
The production release SHALL submit the signed app through Apple `notarytool`, require an `Accepted` result, and staple the app ticket. After generating the website DMG, it SHALL sign the DMG with the same Developer ID and trusted timestamp, separately submit the final DMG, require `Accepted`, and staple the DMG ticket before the artifact can be distributed.

#### Scenario: Credentials are missing
- **WHEN** no complete API key, Apple ID, or Keychain profile credential set is available
- **THEN** production packaging fails with credential setup guidance and does not silently skip notarization

#### Scenario: Apple rejects submission
- **WHEN** notarization returns a status other than `Accepted`
- **THEN** packaging fails and no artifact is declared ready for distribution

### Requirement: Final distribution verification
The release SHALL verify the final application using codesign strict deep validation, Gatekeeper execute assessment, and stapler ticket validation. It SHALL also verify the final DMG using Gatekeeper open assessment and stapler ticket validation before reporting the DMG as ready.

#### Scenario: Final verification succeeds
- **WHEN** signing, notarization, and stapling have completed successfully
- **THEN** all required verification commands pass and the release report records the DMG and app paths

### Requirement: Development and secret isolation
The production workflow SHALL remain separate from local development packaging and SHALL not store Apple private keys, certificates, API keys, or notarization credentials in Git.

#### Scenario: Developer runs local packaging
- **WHEN** the existing local development command is executed
- **THEN** it remains available without being represented as a production Developer ID release

#### Scenario: Sensitive Apple file is created in the workspace
- **WHEN** a `.p8`, `.p12`, provisioning profile, or notary credential file matches repository ignore rules
- **THEN** Git does not include it in version control
