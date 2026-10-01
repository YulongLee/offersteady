## Context

The official Intel 1.3.2 DMG matches the CN manifest hash. It has valid Developer ID signatures, usage descriptions and Hardened Runtime, but neither its app nor helpers have audio-input entitlement. Startup races a permission request against 2500 ms; the recovery function is unused. User approved a Mac-only repair and CN release, without business behavior changes.

## Goals / Non-Goals

**Goals:** Correct signed resource access, truthful permission state, visible recovery, regression coverage, reproducible CN Mac 1.3.3 artifacts.

**Non-Goals:** No model, billing, capture routing, interview mode, device identity, Windows, international deployment, database or backend code changes. Do not enable unpublished mock-interview desktop protocol code. No privacy reset or audio persistence.

## Decisions

- Use the existing 1.3.2 companion source at fa9db78 in an isolated worktree after preserving the full current source in release-20261002.1. This avoids accidentally publishing unrelated desktop changes.
- Add audio-input to main and inherited entitlements; validate actual signed values for the app and helpers, not only source XML or key presence. Retain stable Bundle ID and signing identity.
- Keep the existing boolean permission IPC compatible, deduplicate pending macOS requests in the main process, and read OS status through the existing health IPC. Never impose a deadline on user consent. A dismissed/failed OS request without a definitive status remains retryable rather than inventing denial.
- A Mac-only permission panel owns initialization and manual recovery, independent of network registration. Refresh on focus and explicit checks; discard stale asynchronous results. It uses OS status only and does not open media streams itself. Existing audio monitors/publishers retain their behavior.
- Publish new immutable OSS artifact keys and change only the CN Mac download entries, retaining Windows 1.3.2 and the preceding manifest for rollback. Prefer the existing live-read manifest path over backend restart; verify installed release source behavior before deployment.

## Risks / Trade-offs

- [No physical Intel test machine in this environment] → Automated state tests, x64 binary/entitlement checks and signing/notarization are required; clearly report clean-install Intel acceptance as pending user testing rather than claiming it was run.
- [First launch permission prompt can remain open] → Show pending state without marking denied; settings remain accessible and duplicate requests are prevented.
- [OS/MDM restriction differs from ordinary denial] → Show the OS restriction separately, do not promise to bypass it.
- [Permissions modified while an old refresh is pending] → Sequence async results so stale checks cannot override a newer request.

## Migration Plan

Freeze source; implement/test; build both Mac architectures sequentially; verify signatures, entitlements, notarization and DMG integrity; publish CN metadata only with backups; verify download hashes and public version. Roll back by restoring previous Mac manifest entries. Do not interrupt active interviews.

## Open Questions

The reporting user's macOS version and TCC log are not available; do not claim his exact local failure has been reproduced.
