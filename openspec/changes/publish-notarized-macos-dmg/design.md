## Context

The Electron companion already has separate production commands that create Developer ID signed, Hardened Runtime enabled, notarized, stapled DMGs for arm64 and x64. The publication path is older: it consumes local ZIP metadata, always writes `signingStatus: local-development`, and serves ZIP object keys. This mismatch makes the website advertise development artifacts while verified DMGs remain local.

## Goals / Non-Goals

**Goals:**

- Make verified DMGs the only macOS artifacts eligible for production publication.
- Derive checksum, size, architecture, notarization, and signing status from the actual DMG after validation.
- Preserve the Windows entry when replacing each macOS architecture entry.
- Make publication fail before OSS or manifest mutation if verification fails.
- Keep a reproducible command for building, verifying, publishing, and later rolling back a macOS release.

**Non-Goals:**

- No desktop runtime, audio, screenshot, auto-update, Bundle ID, or version change.
- No Windows signing change.
- No Apple credentials in the repository or on the server.

## Decisions

### Generate production metadata only after the existing verifier passes

The production packaging wrapper will call the existing strict verifier and then emit architecture-specific DMG metadata with `signingStatus: verified`, `notarized: true`, and `developmentOnly: false`. Generating metadata from the actual final file prevents stale ZIP checksums or filenames from entering the public manifest.

Alternative: edit the existing JSON files manually. Rejected because it is not reproducible and could label an unverified file as notarized.

### Make the generic publisher trust only validated production metadata

For macOS production publication, the publisher will require a `.dmg`, `verified`, and `notarized: true`. It will preserve metadata signing state instead of overwriting it with `local-development` and will upload DMGs as `application/x-apple-diskimage`.

Alternative: add a separate one-off upload command. Rejected because future releases would likely repeat the same manifest mismatch.

### Publish architectures independently with fail-safe manifest updates

arm64 and x64 are uploaded one at a time. The publisher replaces only the matching platform/architecture entry, preserving Windows and the other Mac architecture. The website is deployed only after both uploads and local backend tests pass.

Alternative: publish one universal DMG. Rejected because existing native capture runtimes and release validation are architecture-specific.

## Risks / Trade-offs

- [One architecture uploads while the other fails] → Do not deploy the changed manifest until both uploads succeed; the existing online manifest remains active.
- [Incorrect metadata claims notarization] → Generate metadata only after strict codesign, Gatekeeper, and stapler validation and revalidate inside the publication command on macOS.
- [OSS upload succeeds but Git/deployment fails] → The new objects are harmless until the backend manifest is deployed; rerun publication or deploy the verified manifest.
- [Older users rely on ZIP installation] → DMG is the standard macOS direct-distribution format; keep the same bundle ID so existing TCC identity and settings remain stable.

## Migration Plan

1. Add production metadata generation and publisher validation with regression tests.
2. Revalidate both existing 0.1.16 DMGs locally and generate verified metadata.
3. Upload arm64 and x64 DMGs to versioned OSS keys without changing the live website.
4. Verify the resulting manifest contains both Mac DMGs and the unchanged Windows entry.
5. Commit and deploy the backend manifest, then verify public download redirects and downloaded DMG checksums.
6. Roll back by restoring the previous manifest and redeploying; versioned OSS objects can remain without being publicly referenced.

## Open Questions

- A physical Intel Mac installation smoke test remains advisable, but the existing x64 app, native helper architecture, notarization, and Gatekeeper checks are already accepted and sufficient for this controlled publication.
