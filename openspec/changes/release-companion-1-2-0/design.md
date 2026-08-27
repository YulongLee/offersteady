## Context

Companion 1.1.9 is an installed local acceptance candidate built from commits `458fe3c` and `fcf81aa`. On the physical Apple Silicon Mac it preserved the active pairing identity, captured system audio continuously, received per-frame Backend acknowledgements with zero sequence gaps, and remained alive when the only headset microphone was removed. Production distribution requires a new immutable version, release-grade macOS signing/notarization, supported-platform metadata, atomic manifest publication, and deployment verification.

## Goals / Non-Goals

**Goals:**

- Release the accepted code as companion 1.2.0 without changing runtime behavior after acceptance.
- Produce independently verifiable artifacts for macOS arm64, macOS x64, and Windows x64.
- Publish only artifacts whose hashes, architecture, signature status, and distribution status are accurately represented.
- Update the production manifest atomically and verify the public website, APIs, and downloads.
- Preserve 1.1.x artifacts and a server/backend rollback point.

**Non-Goals:**

- No new capture, ASR, transcript, UI, prompt, or protocol feature work during release.
- No claim that an unsigned Windows installer is code-signature verified.
- No deletion of prior local or remote release artifacts.
- No persistence of raw audio or transcript content for release validation.

## Decisions

### Use semantic version 1.2.0 for the requested 1.2 release

The package and all artifact metadata will use `1.2.0`, keeping compatibility with the existing three-component semantic versions. A two-component `1.2` string was rejected because build, updater, and manifest tooling already consume semantic versions.

### Rebuild every artifact from the committed release source

The version bump, OpenSpec artifacts, and release documentation will be committed before production packaging. macOS arm64 and x64 will use the release scripts with Developer ID signing, Hardened Runtime, notarization, stapling, Gatekeeper, and architecture verification. Re-labeling 1.1.9 local artifacts was rejected because it would break artifact identity and provenance.

### Preserve truthful platform-specific trust status

Both macOS artifacts must pass the production verification gate. Windows x64 will be packaged and structurally validated; if no Windows code-signing certificate is available, its metadata remains `local-development`/unsigned and the website must not describe it as verified. Blocking macOS release on an unavailable Windows certificate was rejected because the manifest supports independent trust status per platform.

### Publish immutable objects before the manifest and deploy last

The publisher uploads versioned artifacts first, verifies hashes, then atomically updates the local production manifest. Only after the manifest commit is pushed will the Backend be deployed. If any artifact or upload fails, the existing production manifest remains unchanged. Partial manifest updates were rejected because they can expose missing downloads.

## Risks / Trade-offs

- [Apple notarization credentials are unavailable or rejected] → Stop before publication; do not downgrade to ad-hoc signing.
- [Cross-architecture macOS build produces the wrong native helper] → Verify both the app executable and native capture runtime with `lipo`/release verifier.
- [Windows remains unsigned] → Publish only with explicit unverified status and retain the existing warning in the website.
- [Manifest deploy fails after immutable upload] → Existing production manifest remains active; uploaded versioned objects are harmless and can be referenced by a later retry.
- [Backend deployment regresses unrelated services] → Rebuild/restart only the Backend service, retain the prior image/commit, and verify public health before completion.

## Migration Plan

1. Bump package metadata to 1.2.0, update release notes, and run all automated verification.
2. Commit and push the release source.
3. Build and verify macOS arm64/x64 production artifacts and the Windows x64 installer.
4. Upload artifacts and generate the atomic production manifest.
5. Commit/push the manifest, tag the prior Backend image, deploy Backend only, and verify health/state/downloads.
6. Roll back by restoring the prior manifest/Backend image; immutable 1.1.x artifacts remain available.

## Open Questions

None.
