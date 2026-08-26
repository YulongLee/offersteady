## Context

Electron currently derives `userData` from the launch context. A normal packaged launch uses `Application Support/面试稳伴随程序`, while recent local acceptance launches supplied `--user-data-dir=.../@offersteady/desktop`. Both directories can hold different device identities and diagnostics, so restarting the same signed app can silently attach a different companion device. Separately, `desktopCapturer.getSources` is attempted after macOS denies screen capture; repeated display-media requests generate noisy failures and can leave computer audio unavailable while microphone capture remains healthy.

## Goals / Non-Goals

**Goals:**

- Give all packaged and development launches one stable user-data location.
- Preserve an existing pairing identity without overwriting a newer stable identity.
- Make system-audio permission denial explicit, contained, and recoverable after authorization/restart.
- Keep microphone capture and the existing 1.1.8 transport recovery behavior intact.
- Produce a verifiable 1.1.9 macOS acceptance build and retain 1.1.8 for rollback.

**Non-Goals:**

- Do not bypass macOS TCC or capture computer audio without user consent.
- Do not merge arbitrary Chromium caches, diagnostics, transcripts, screenshots, or raw audio.
- Do not change Backend protocol, ASR provider/model, transcript delivery, or billing.
- Do not publish 1.1.9 to production before local permission and live-capture acceptance.

## Decisions

### Pin a stable product-owned user-data path before Electron readiness

The main process will set `userData` to `<appData>/@offersteady/desktop` before stores, sessions, or windows are initialized. This matches the directory used by the active acceptance identity and is independent of localized `productName`, executable name, or launch method. Continuing to rely on Electron's derived product-name path was rejected because renames and launch arguments can fork identity again.

### Migrate only an allowlisted identity bundle when the stable path is empty

Before selecting the stable path, bootstrap logic will inspect the previous product-name directory. If the stable directory has no pairing identity, it will copy the pairing file and, when present, its encrypted credential as one identity bundle. Screenshot shortcut settings may be copied independently when absent. Existing destination files are never overwritten, and Chromium cache, diagnostics, media, and application content are never migrated. Copying whole directories was rejected because it mixes volatile caches and can overwrite the identity currently bound to an interview.

### Gate display-source acquisition on the operating-system permission state

On macOS, the app will check `systemPreferences.getMediaAccessStatus("screen")` before `desktopCapturer.getSources`. A non-granted state returns a typed denied result immediately and opens System Settings only after an explicit user action. The display-media handler will attach rejection handling synchronously and contain callback errors, so denial does not produce unhandled promise rejections or a retry storm. Pretending the channel is ready or repeatedly probing denied TCC was rejected because both obscure the real failure.

### Isolate degraded system audio from microphone capture

Permission denial marks only system audio unavailable and supplies actionable copy. The microphone publisher remains active. Once the user grants permission, a full app restart re-evaluates TCC and re-enters the existing bounded capture recovery path. Programmatic TCC mutation was rejected because macOS requires user consent and stable signed identity.

## Risks / Trade-offs

- [A legacy installation has a valid identity in both directories] → The stable destination always wins; no automatic overwrite or identity blending occurs.
- [A legacy pairing file exists without its credential] → Copy the valid pairing identity and allow normal re-registration; never invent or print credentials.
- [macOS still reports denied immediately after the user toggles access] → Show that a full app restart is required and retry only on the new process.
- [Changing `userData` affects local browser session caches] → Only product metadata is relied on; users may need to re-pair only if neither known identity file exists.

## Migration Plan

1. Add and test stable-path resolution and allowlisted migration.
2. Add and test typed screen-permission/display-source handling.
3. Increment to 1.1.9, run full Desktop verification, and build a signed local macOS artifact.
4. Quit 1.1.8, install 1.1.9 without deleting either data directory, and verify the active pairing identity is preserved.
5. Obtain user TCC consent, restart 1.1.9, and validate live computer-audio frames plus Backend acknowledgements.
6. Roll back by reinstalling the retained 1.1.8 app; local identity files remain untouched.

## Open Questions

None.
