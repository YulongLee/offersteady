## 1. Baseline and regression coverage

- [x] 1.1 Add deterministic desktop fixtures for clear silence, quiet trailing speech, resumed pauses, and source-specific adaptive release bounds
- [x] 1.2 Add backend queue regressions proving terminal ordering, same-segment PCM preservation, and cross-source isolation
- [x] 1.3 Add gateway regressions for post-commit partial delivery, final authority, and disabled-by-default silence flush
- [x] 1.4 Add Web regressions for post-commit growth, shorter-draft preservation, final correction, and partial-after-final rejection

## 2. Desktop endpoint and transport

- [x] 2.1 Implement bounded source-specific adaptive release durations using existing noise and temporal activity evidence
- [x] 2.2 Preserve final PCM ordering and add privacy-safe speech-end and terminal-enqueue diagnostics
- [x] 2.3 Increment desktop package and lock metadata to 1.2.11 without layout, icon, identity, permission, endpoint, or protocol changes

## 3. Backend provider tail path

- [x] 3.1 Prioritize/coalesce admitted terminal work per source without overtaking earlier PCM
- [x] 3.2 Record terminal queue, commit-to-last-partial, commit-to-final, and final-added-character evidence without transcript content
- [x] 3.3 Add a bounded zero-PCM suffix experiment behind a disabled-by-default setting while retaining manual commit and the current final timeout
- [x] 3.4 Ensure unseen provider partials remain publishable after terminal admission until completed and cannot reopen a final segment

## 4. Web reconciliation

- [x] 4.1 Apply equal-or-longer post-commit revisions immediately without reactivating the transcript caret
- [x] 4.2 Preserve longer non-final text across shorter provider hypotheses while allowing authoritative final correction
- [x] 4.3 Record content-free last-visible-revision and final-added-character presentation evidence

## 5. Verification and local acceptance

- [x] 5.1 Run focused then full Desktop, Backend, Web, and protocol test suites plus relevant typechecks
- [x] 5.2 Run production builds, cross-platform package/build validation available on the host, and strict OpenSpec validation
- [x] 5.3 Open the local Apple Silicon 1.2.11 companion against the unchanged online service for user acceptance without deploying or reconfiguring production
