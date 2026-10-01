## 1. Baseline and scope

- [x] 1.1 Freeze and push current source and release tag; isolate the released 1.3.2 desktop baseline
- [x] 1.2 Verify existing desktop permission specs and validate this approved change

## 2. Repair

- [x] 2.1 Add audio-input entitlements and enforce actual signed entitlement values in release verification
- [x] 2.2 Replace timed-out denial with truthful OS status and single-flight consent requests
- [x] 2.3 Add a Mac-only permission recovery panel independent of backend registration
- [x] 2.4 Bump desktop and lockfile to 1.3.3 without changing capture or business protocols

## 3. Verification

- [x] 3.1 Add and run regressions for delayed grant, denial, restriction, duplicate requests, failures, focus refresh and stale/unmounted callbacks
- [x] 3.2 Run full desktop tests, typecheck, build and scope review
- [ ] 3.3 Build and verify signed/notarized Intel and Apple Silicon DMGs; document physical-device coverage limitations

## 4. CN publication

- [ ] 4.1 Publish immutable Mac artifacts to OSS and back up the current CN manifest
- [ ] 4.2 Update CN download metadata only; verify versions, hashes, health and unchanged Windows/international entries
- [ ] 4.3 Commit and push the repair, update release notes and hand off user acceptance steps
