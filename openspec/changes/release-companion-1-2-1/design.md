## Context

The accepted 1.2.0 UI and application identity must remain unchanged. Runtime diagnostics found two non-UI recovery defects: a missing transport could exhaust a retry budget and remain disconnected, and a newly started renderer reused source generation 1 while the live backend session retained a higher generation. The latter caused the backend to reject frames as stale before sequence acknowledgement could advance. macOS development runs also use a different code identity from a Developer ID release and therefore do not provide valid evidence about production privacy-grant reuse.

## Goals / Non-Goals

**Goals:**

- Ship a patch-only 1.2.1 release with the 1.2.0 layout, icon, Bundle ID, and workflow unchanged.
- Make a desktop process restart resume both authoritative channel sequence offsets and source generations.
- Preserve bounded single-flight retry behavior without a permanent transient-failure terminal state.
- Produce verifiable macOS arm64/x64 release artifacts with the existing Developer ID identity.
- State privacy authorization behavior accurately and preserve 1.2.0 as rollback.

**Non-Goals:**

- No renderer layout, CSS, icon, prompt, feature, ASR model, billing, or protocol-version change.
- No attempt to bypass or silently grant macOS microphone or screen/system-audio privacy permissions.
- No production publication or deployment without a separate explicit release instruction.
- No persistence of audio or transcript content for verification.

## Decisions

### Resume source generations through the existing connection-state handshake

The gateway adds optional `resumeSourceGenerations` values beside `resumeOffsets`. Receipts persist the accepted generation, and the in-memory authority is also considered so even a generation observed before receipt completion is retained. A restarted publisher seeds each new segmenter with the authoritative generation and emits the next generation. A timestamp-derived client generation was rejected because client clocks are not an authoritative session ordering source.

### Keep the handshake backward compatible

The protocol version remains 2.0. Old clients ignore the additional field; new clients default missing values to zero when talking to an older server. The server must be available with the added field before same-session restart acceptance is claimed. A protocol-breaking version bump was rejected because no existing field changes meaning.

### Treat 1.2.1 as a UI-invariant patch

The release gate compares the changed source set and rejects renderer layout, stylesheet, asset, icon, product name, or Bundle ID changes. Development-window chrome is not a production UI baseline. Rebuilding the UI was rejected because it is unrelated to the transport defect and conflicts with the accepted product layout.

### Use the established production identity for macOS

Both macOS architectures use `com.offersteady.companion`, the existing Developer ID certificate, Hardened Runtime, notarization, and stapling. This maximizes the chance that macOS recognizes an in-place upgrade and reuses an existing grant, but user-controlled TCC authorization remains authoritative. Ad-hoc signing or claiming that Apple account access can pre-authorize privacy permissions was rejected.

## Risks / Trade-offs

- [Backend is not yet updated] → The new client safely defaults the optional field, but same-session process restart is not accepted until the compatible backend is deployed.
- [Apple signing or notarization credentials fail] → Stop before presenting the artifact as a production build; do not fall back to ad-hoc signing.
- [macOS still requests permission] → Explain that TCC is user controlled, verify designated requirement and Bundle ID, and provide direct System Settings guidance.
- [Windows certificate is unavailable] → Build and structurally validate the installer while labeling signing status truthfully.
- [Patch changes UI assets accidentally] → Fail the release gate and remove the unrelated changes before packaging.

## Migration Plan

1. Add the backward-compatible resume-generation field and regression tests.
2. Run Desktop, Backend compatibility, build, typecheck, and strict OpenSpec validation.
3. Bump only package/release metadata to 1.2.1 and verify UI-invariant source paths.
4. Build and verify signed/notarized/stapled macOS arm64 and x64 artifacts; structurally verify Windows x64.
5. Deliver local immutable artifacts for acceptance. Publish/deploy only after explicit authorization.
6. After explicit authorization, commit and push the verified source, upload immutable artifacts, atomically update the production manifest, tag the release, and deploy Backend only.
7. Roll back by restoring the 1.2.0 manifest and retained Backend image; do not delete immutable 1.2.1 objects or restart PostgreSQL, Redis, or Web.

## Open Questions

None.
