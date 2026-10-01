## ADDED Requirements

### Requirement: Correct Windows package
The CN Windows x64 installer SHALL contain companion version 1.3.4, the existing OfferSteady.exe launch target and protocol 2.0. It MUST NOT include macOS native binaries, secrets or unpublished desktop features.

#### Scenario: Inspect the package
- **WHEN** the installer is built from the approved 1.3.3 source plus the original-design restoration and 1.3.4 version update
- **THEN** the embedded application version and launch entry match, the runtime is x64, and the Mac-only permission panel remains inactive on Windows

### Requirement: Scoped publication
The publisher SHALL update only approved CN entries, preserve all unapproved entries and international releases, and keep prior artifacts recoverable. It MUST NOT mark unsigned Windows artifacts as verified or notarized. The subsequently approved three-platform 1.3.4 publication may update Mac entries through the accompanying Mac change.

#### Scenario: Publish Windows 1.3.4 after separate confirmation
- **WHEN** the validated installer is uploaded and activated
- **THEN** CN Windows reports 1.3.4 with matching size/hash and a working download, accompanying approved Mac updates are included in the complete manifest, and international entries remain unchanged

#### Scenario: Repackaging only
- **WHEN** the user requests repackaging without resuming publication
- **THEN** the validated local installer is delivered without OSS uploads, production metadata changes or service restarts

### Requirement: Non-disruptive release verification
The release SHALL pass relevant automated tests and package checks before publication, check that no interview is live before switching, and verify public health without restarting business services. Physical Windows installation/audio tests MUST NOT be claimed when not performed.

#### Scenario: Complete the release
- **WHEN** publication finishes
- **THEN** the running service identity/start time are unchanged, public downloads and health pass, and remaining physical-device acceptance is disclosed
