## 1. Compatibility build plumbing

- [x] 1.1 Parameterize the macOS native runtime deployment target with a 14.2 default
- [x] 1.2 Add an isolated Ventura 13.4 arm64 packaging script and npm command
- [x] 1.3 Generate separate artifact metadata and keep the online release directories untouched

## 2. Verification

- [x] 2.1 Run desktop typecheck/tests and the compatibility build
- [x] 2.2 Verify app minimum OS, arm64 architecture, signature, DMG structure, and SHA-256
- [x] 2.3 Record that real macOS Ventura 13.4 microphone/system-audio/screen capture acceptance remains required
