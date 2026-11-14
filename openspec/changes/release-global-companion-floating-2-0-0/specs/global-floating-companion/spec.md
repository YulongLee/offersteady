## ADDED Requirements

### Requirement: Open a capture-protected Global floating workspace

The Global desktop companion SHALL offer a floating workspace using the existing Global website and desktop binding. Supported operating systems SHALL be asked to exclude the window from compatible capture. The companion SHALL report the protection request separately from receiver-side compatibility.

#### Scenario: A Global user opens the floating workspace

- **WHEN** a Global user opens the floating workspace from the tray
- **THEN** the companion presents the existing Global sign-in and interview preparation in an isolated view and retains the existing device identity and original capture flow

#### Scenario: A Global user previews the display on macOS

- **WHEN** the user requests a preview or screenshot from the companion
- **THEN** the image excludes companion windows and a failure to obtain the filtered image is reported

### Requirement: Publish verified Global downloads

The release SHALL preserve Global configuration and historical downloads. Public release metadata SHALL advance only after all artifacts pass the existing signing, integrity and release gates.

#### Scenario: A candidate fails validation

- **WHEN** a platform fails package or release verification
- **THEN** Global public release metadata continues to serve the currently verified release

#### Scenario: A verified candidate is published

- **WHEN** the three Global packages and release gates pass
- **THEN** current download entries expose the new Global package checksums and previously published filenames remain available
