## 1. Preparation

Publication paused on 2026-10-02 at the user's request to preserve the original assistant design. Finish and validate that correction before resuming any Windows build/publication; the published Mac 1.3.3 artifacts remain unchanged.

Subsequent user request resumes local repackaging only as version 1.3.4. Tasks 1–2 are approved for completion; section 3 remains deferred pending publication confirmation.

After package delivery, the user explicitly authorized the online update. Section 3 is now approved, combined with the two approved Mac 1.3.4 entries in one CN manifest switch.

- [x] 1.1 Confirm approved 1.3.3 source, existing Windows packaging and scope
- [x] 1.2 Validate this change and add Windows platform isolation regression

## 2. Validation and packaging

- [x] 2.1 Run desktop tests, typecheck and download/publication regressions
- [x] 2.2 Build x64 installer and inspect payload, executable architecture, version, entrypoint and signing metadata

## 3. CN release

- [ ] 3.1 Back up existing manifests and upload the Windows installer; verify remote full hash
- [ ] 3.2 With no live interviews, update CN metadata only; verify health and unchanged Mac/international artifacts
- [ ] 3.3 Record release, commit/push and disclose remaining Windows physical acceptance

Local 1.3.4 packaging verified 2026-10-02: 223 desktop tests, 5 web platform tests, 8 backend download/publication tests and desktop typecheck passed. NSIS installer was extracted and its embedded app-64.7z payload checked: OfferSteady.exe is PE x64, app package version is 1.3.4, entrypoint exists, renderer assets match the original-layout build, protocol remains 2.0, no Mac native payload or credential files are bundled. Installer is 102153689 bytes, SHA-256 `24eb5aca547757158b9bffc0b78e2f63195d1adafa75b51db6bdccf53f183f53`. PE certificate table is empty, matching `local-development` / `notarized: false`. Physical Windows install/audio tests have not been performed. No OSS upload or online manifest switch occurred.
