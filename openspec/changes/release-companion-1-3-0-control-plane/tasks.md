## 1. Local release metadata

- [x] 1.1 Update the desktop package version to 1.3.0 without changing root or online release metadata
- [x] 1.2 Add regression coverage for the 1.3.0 version boundary and local-only release scope

## 2. Control-plane verification

- [x] 2.1 Verify 10-second binding polling and existing bounded failure backoff
- [x] 2.2 Verify single-flight scheduling and preserve existing media/protocol behavior

## 3. Local build and handoff

- [x] 3.1 Run focused desktop tests, typecheck, and local build
- [x] 3.2 Start the local companion for user acceptance without invoking online deployment
- [x] 3.3 Validate the OpenSpec change strictly and record the executed verification
