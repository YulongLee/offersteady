## 1. Authorization and fresh baseline

- [x] 1.1 Record 2026-11-02 CN companion-only production authorization and exclusions; validate apply-ready contract.
- [x] 1.2 Freeze actual component lifecycle, fixed Backend image/Compose inputs, current manifest, business input hashes and OSS settings without exporting private configuration.

## 2. Official three-platform artifacts

- [x] 2.1 Verify current inputs match tested Local-r3 source/dist; run relevant release checks and preserve immutable source evidence.
- [x] 2.2 Prepare and verify macOS arm64 official DMG with actual signatures/audio entitlements, App/DMG notarization, staple, Gatekeeper and payload equality.
- [x] 2.3 Prepare and verify macOS x64 official DMG with the same requirements, serially after arm64 freeze/verification.
- [x] 2.4 Verify Windows x64 final NSIS outer/inner payload, architecture, frozen dist and truthful unsigned metadata.

## 3. Guarded publication preparation

- [x] 3.1 Confirm OSS latest is not a runtime source and remains unchanged; upload or verify immutable version objects and fully read back all three sizes/SHA-256 before public manifest mutation.
- [x] 3.2 Implement and test the dedicated no-restart controller: actual fixed-image baseline, all-input/lifecycle drift checks, manifest CAS, known-state lost-response handling and guarded rollback.
- [x] 3.3 Stage and verify the actual-base plus single-manifest-layer candidate and fixed-image future-recreate Compose overlay without changing historical Compose or unrelated tags.

## 4. Publish and verify

- [x] 4.1 Repeat baseline guards and atomically publish all three official CN entries without changing OSS latest, restarting containers or deploying pending business code.
- [x] 4.2 Verify public versions, all three Range/full downloads, actual bytes/MIME and unchanged component lifecycle/business files; confirm known-state completion or guarded recovery.
- [x] 4.3 Record production result, upgrade-gate behavior, local-only Web/Backend exclusions, physical-device limits, future-recreate instructions and exact rollback; run strict OpenSpec/link checks.

执行结果见[2026-11-02正式发布记录](../../../docs/releases/companion-1.3.6-cn-20261102.md)。01:26:04北京时间切换国服三平台下载清单，实际业务容器不变。三包Range/完整下载、完整源与配置、历史Compose、OSS latest及只读验收通过；本地Web/Backend配套未发布，未提交/推送Git。首次配置校验对Docker两项Mount返回顺序产生误报，已以完整原摘要精确复原证据和14项回归修正只读验收，不改基线、服务、挂载字段或再次apply；原发布版70项、修订验收版84项分开记录。
