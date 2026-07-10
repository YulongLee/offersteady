## 1. Restore prototype-facing files

- [x] 1.1 Review the current prototype-facing files affected by backend integration and confirm the approved baseline behavior
- [x] 1.2 Restore `apps/web/src/LibraryManager.tsx` to the approved prototype presentation and interaction flow
- [x] 1.3 Restore `apps/web/src/material-upload-adapter.ts` to a compatibility-first adapter that does not change prototype behavior

## 2. Preserve compatibility without changing product behavior

- [x] 2.1 Keep only the minimum protocol compatibility required for the restored prototype to compile and run
- [x] 2.2 Verify that backend capability changes remain isolated behind adapters rather than altering page behavior

## 3. Verification and documentation

- [x] 3.1 Validate that the restored prototype still typechecks and its core prototype flows behave as expected
- [x] 3.2 Document the prototype-integrity boundary so future backend integration work does not silently change approved UI behavior
- [x] 3.3 Run `openspec validate restore-approved-web-prototype --strict`
