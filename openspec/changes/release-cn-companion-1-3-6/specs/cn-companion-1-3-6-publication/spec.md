## ADDED Requirements

### Requirement: Official CN 1.3.6 packages match tested inputs
The release SHALL publish version 1.3.6 for macOS arm64, macOS x64 and Windows x64 from the tested Local-r3 desktop inputs. Stable product identity, protocol, CN service defaults, Electron version and minimum supported operating systems SHALL remain unchanged. Packages SHALL exclude local/Global runtime overrides, compiled tests and server credentials.

#### Scenario: One architecture differs from the tested source
- **WHEN** a production artifact does not match its frozen tested source, built runtime files or native payload
- **THEN** publication stops before the public manifest changes

#### Scenario: A local Mac package has not passed formal publication checks
- **WHEN** a candidate is only a prepare-only or Local-r3 unnotarized DMG
- **THEN** renaming the file or changing metadata does not make it production-publishable

#### Scenario: A Mac artifact is ready
- **WHEN** an official DMG is accepted for publication
- **THEN** its actual App and Mach-O components pass Developer ID identity, architecture and audio-input entitlement checks, its App and DMG pass notarization/stapler/Gatekeeper checks, and its contained payload matches frozen inputs

#### Scenario: A Windows artifact is ready on a non-Windows build host
- **WHEN** the Windows installer is accepted for publication
- **THEN** its outer/inner archives and installed payload are verified against the frozen x64 build, and metadata reports its actual unsigned status without claiming physical-device audio acceptance

### Requirement: Immutable artifacts precede the public version switch
All three CN immutable version objects SHALL be completely read back and checked for exact length and SHA-256 before the public manifest can switch. Existing objects with different bytes SHALL not be overwritten. OSS latest files, which are not read by the current website or version gate, SHALL remain unchanged.

#### Scenario: A versioned object already exists with different content
- **WHEN** the target 1.3.6 object exists but its complete downloaded bytes differ from the verified artifact
- **THEN** publication stops and the current public manifest remains unchanged

#### Scenario: An artifact is missing or fails readback
- **WHEN** any requested architecture fails upload, full readback or integrity checks
- **THEN** none of the three public version entries is advanced

#### Scenario: All immutable objects are ready
- **WHEN** all three complete remote objects match verified artifacts
- **THEN** only those exact filenames, sizes, hashes and immutable CN keys may enter the candidate public manifest

### Requirement: The runtime manifest publishes atomically without restarting services
The publication controller SHALL use the actual running fixed Backend image, container lifecycle, configuration and complete authorized input baseline. It SHALL change only the runtime desktop release manifest using a guarded same-directory atomic replacement. It SHALL not restart, recreate or replace Backend, Web, worker or other business components.

#### Scenario: Production differs from the reviewed baseline
- **WHEN** a container, source/configuration input, mounted path, current manifest or reviewed image has drifted before publication
- **THEN** the controller stops without overwriting the unknown state

#### Scenario: Docker reverses the order of two unchanged mount records
- **WHEN** Docker inspection returns the same two complete mount objects in reverse order and swapping only those objects exactly reproduces the frozen whole configuration digest
- **THEN** read-only verification accepts the unchanged configuration without rewriting the baseline, ignoring any fields, reapplying publication or restarting services

#### Scenario: Three verified release entries are published
- **WHEN** all package checks and repeated baseline guards pass
- **THEN** all three entries become visible together through one manifest compare-and-swap, and component IDs, images, startup times and restart counts remain unchanged

#### Scenario: An old helper is already bound to a running interview
- **WHEN** the manifest advances to 1.3.6
- **THEN** publication does not actively terminate that bound session, while existing new-bind/start version checks require an eligible current helper

### Requirement: Future recreation uses explicit reviewed release materials
Publication SHALL retain a candidate built from the actual running Backend image with exactly one additional manifest-only layer, unchanged image Config, unchanged original RootFS prefix and unchanged business inputs. A fixed-candidate-image Compose overlay SHALL be saved for future explicitly authorized recreation. Historical Compose files and unrelated image tags SHALL remain unchanged.

#### Scenario: The active Compose configuration already pins an image SHA
- **WHEN** the old compose-backend latest tag does not refer to that actual running image
- **THEN** publication does not rewrite that tag or historical Compose files and uses a dedicated verified candidate plus explicit fixed-image overlay

#### Scenario: A later operator plans to recreate the Backend
- **WHEN** a future release uses this publication's restart-safe materials
- **THEN** it explicitly includes the saved fixed-candidate overlay or carries the exact active manifest into a newly verified candidate, rather than assuming hot replacement changed historical image contents

### Requirement: Publication is verifiable and recoverable within the CN companion scope
The release SHALL preserve the prior exact manifest, release/object evidence and guarded recovery plan. Unknown or drifted states SHALL stop automatic recovery. Public validation SHALL check all three versions, Range/full download bytes and MIME, and unchanged service lifecycle. No pending Web/Backend business logic, Global release, OSS latest mutation, Git push, production model call, real interview or load test SHALL be included.

#### Scenario: SSH returns no reliable publication receipt
- **WHEN** the manifest switch result is uncertain
- **THEN** the controller reads actual state and confirms only known matching old/new manifest states; it does not blindly replay or overwrite a third state

#### Scenario: A verified known release must be rolled back
- **WHEN** rollback is explicitly invoked while release ownership and current known hashes still match
- **THEN** the exact prior public manifest is restored without deleting immutable artifacts, changing OSS latest, replacing business images or terminating interviews

#### Scenario: Public verification succeeds
- **WHEN** the release is reported complete
- **THEN** all three public downloads match final verified artifacts, the report identifies physical-device limits, and local-only Web/Backend screenshot-read and feedback improvements are not claimed as deployed
