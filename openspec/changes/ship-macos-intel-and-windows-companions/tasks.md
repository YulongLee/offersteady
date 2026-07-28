## 1. Runtime

- [x] 1.1 Make runtime capability and permission diagnostics platform-aware
- [x] 1.2 Enable Windows Electron loopback ownership without starting the macOS native helper
- [x] 1.3 Compile the macOS native helper for an explicit target architecture

## 2. Packaging and Publishing

- [x] 2.1 Add architecture-correct macOS Intel and Windows x64 package commands
- [x] 2.2 Generate normalized SHA-256 release metadata for builder artifacts
- [x] 2.3 Generalize OSS paths and merge published platform entries
- [x] 2.4 Generalize backend local artifact discovery and download file types

## 3. Product Surface and Documentation

- [x] 3.1 Make the Web download center and installation guidance platform-aware
- [x] 3.2 Document cross-platform test packaging, publishing, and signing limitations

## 4. Verification

- [x] 4.1 Validate the OpenSpec change
- [x] 4.2 Build the shared desktop application
- [x] 4.3 Package and inspect macOS Intel x64 artifact architecture
- [x] 4.4 Package and inspect Windows x64 archive contents

## 5. Windows Installer

- [x] 5.1 Build the verified portable directory into a single NSIS setup executable
- [x] 5.2 Add desktop, Start Menu, installation-directory, and uninstall behavior
- [x] 5.3 Publish installer-aware metadata and download-center guidance

## 6. Windows Installer Shortcut Repair

- [x] 6.1 Pin the Windows executable name so NSIS shortcuts and the packaged application target the same file
- [x] 6.2 Add a regression test and packaging-time validation for the Windows executable and installer
- [x] 6.3 Rebuild, publish, and verify the Windows 0.1.1 installer through the production download flow
