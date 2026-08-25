## Context

The repository currently identifies the companion as 0.1.20 while production serves macOS 0.1.19 and Windows 0.1.16. The user approved a coordinated Release 1.1 publication for the three supported desktop targets and the current web/backend code.

## Goals / Non-Goals

**Goals:**

- Produce one auditable 1.1.0 desktop baseline for macOS arm64, macOS x64, and Windows x64.
- Reuse the proven macOS Developer ID and notarization pipeline.
- Keep `com.offersteady.companion` stable.
- Publish only after tests and artifact validation pass.

**Non-Goals:**

- No new realtime, ASR, RAG, LLM, billing, or UI behavior in this release task.
- No Windows signing claim without an available Authenticode certificate.
- No replacement of the existing deployment architecture.

## Decisions

1. The application semantic version is `1.1.0`; the repository release tag is `release-1.1`.
2. Both macOS builds must pass Developer ID signing, Hardened Runtime, notarization, stapling, codesign verification, Gatekeeper assessment, and stapler validation.
3. The Windows x64 NSIS installer remains explicitly marked with its actual signing state and must pass the repository installer validation.
4. Artifact publication updates all three platform/architecture entries atomically where possible, then the generated manifest is committed before production deployment.
5. Production deployment is accepted only when Backend health, Web runtime state, and all three desktop download entries are verified online.

## Rollback

Keep prior OSS artifacts addressable. If production verification fails, restore the prior desktop manifest and redeploy the previous Git commit; the stable Bundle Identifier and unchanged API protocol allow existing clients to continue operating.
