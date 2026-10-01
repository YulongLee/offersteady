## Context

The official Intel 1.3.2 DMG matches the CN manifest hash. It has valid Developer ID signatures, usage descriptions and Hardened Runtime, but neither its app nor helpers have audio-input entitlement. Startup races a permission request against 2500 ms; the recovery function is unused. User approved a Mac-only repair and CN release, without business behavior changes.

## Goals / Non-Goals

**Goals:** Correct signed resource access, truthful permission state, recovery without redesign, regression coverage, reproducible CN Mac artifacts.

**Non-Goals:** No model, billing, capture routing, interview mode, device identity, Windows, international deployment, database or backend code changes. Do not enable unpublished mock-interview desktop protocol code. No privacy reset or audio persistence.

## Decisions

- Use the existing 1.3.2 companion source at fa9db78 in an isolated worktree after preserving the full current source in release-20261002.1. This avoids accidentally publishing unrelated desktop changes.
- Add audio-input to main and inherited entitlements; validate actual signed values for the app and helpers, not only source XML or key presence. Retain stable Bundle ID and signing identity.
- Keep the existing boolean permission IPC compatible, deduplicate pending macOS requests in the main process, and read OS status through the existing health IPC. Never impose a deadline on user consent. A dismissed/failed OS request without a definitive status remains retryable rather than inventing denial.
- Following the user's 2026-10-02 correction, a non-rendering Mac-only hook owns initialization, independent of network registration. Refresh on focus, visibility and activation of the existing microphone selector; discard stale asynchronous results. It uses OS status only and does not open media streams itself. The prior 1.3.2 visual layout, styles, rows and button positions are preserved; no permission panel or extra buttons are added. OS settings remain the recovery path for denied/restricted access.
- Publish new immutable OSS artifact keys and change only the CN Mac download entries, retaining Windows 1.3.2 and the preceding manifest for rollback. Prefer the existing live-read manifest path over backend restart; verify installed release source behavior before deployment.

## Risks / Trade-offs

- [No physical Intel test machine in this environment] → Automated state tests, x64 binary/entitlement checks and signing/notarization are required; clearly report clean-install Intel acceptance as pending user testing rather than claiming it was run.
- [First launch permission prompt can remain open] → Keep pending state without marking denied; duplicate requests are prevented. Permission detail is available via the existing microphone selector's tooltip without adding layout space.
- [OS/MDM restriction differs from ordinary denial] → Show the OS restriction separately, do not promise to bypass it.
- [Permissions modified while an old refresh is pending] → Sequence async results so stale checks cannot override a newer request.

## Migration Plan

Freeze source; implement/test; build both Mac architectures sequentially; verify signatures, entitlements, notarization and DMG integrity; publish CN metadata only with backups; verify download hashes and public version. Roll back by restoring previous Mac manifest entries. Do not interrupt active interviews.

The user-requested layout correction is local-only pending validation/release confirmation. It must not replace the bytes behind already published 1.3.3 keys or silently resume the Windows publication paused for this correction.

The subsequent repackaging request approves local 1.3.4 Mac builds and their standard Apple notarization checks. Archive prior local 1.3.3 output before the architecture-scoped packaging cleanup. Build architectures sequentially because native output and renderer dist are shared. Leave production download manifests and servers untouched.

The user's subsequent online-update instruction resumes CN 1.3.4 publication. Activate the Mac and separately approved Windows entries in one complete manifest after all artifacts pass full remote hash verification. Base the metadata-only image on the current compose image rather than this older desktop worktree's backend code. Preserve container identity/start time, back up runtime/source/OSS manifests, guard concurrent deployment by image/hash checks and provide rollback to the preceding complete manifest.

## Open Questions

The reporting user's macOS version and TCC log are not available; do not claim his exact local failure has been reproduced.
