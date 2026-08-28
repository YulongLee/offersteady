## Context

The desktop companion currently has two related identity/navigation regressions. Commit `2bb21e4` introduced transparent RGBA package and renderer icons, but commit `5ade1ea` replaced both with opaque RGB white-canvas images and rewrote the tests to pin that state. Separately, the connection action reads the authoritative active binding and constructs `/app/interviews/{sessionId}/live`, so clicking it bypasses the Web workspace and immediately enters the bound interview.

Version 1.2.4 remains protocol-compatible with 1.2.3. ARM production observation found a healthy audio hot path but exposed four orchestration defects: the desktop can wait up to ten seconds to notice a newly-live binding; the start request can wait 2.5 seconds for prewarm; seven of nine observed system turns ended only at the 12-second maximum; and recovered health fields plus snapshot-only runtime delivery can leave the Web in a false error state.

## Goals / Non-Goals

**Goals:**

- Restore a transparent, text-free icon that remains legible in the macOS Dock, Finder, Windows shell, installer, and companion header.
- Make the primary website action open the configured workspace root (`/app`) regardless of binding state.
- Publish consistent 1.2.4 assets for macOS arm64, macOS x64, and Windows x64 with deterministic validation.
- Make live capture start promptly after the Web session becomes live.
- Bound end-of-speech latency and expose a metric measured from the last meaningful speech sample.
- Recover the Web health banner automatically after the underlying source recovers.

**Non-Goals:**

- Change the companion layout, permission grants, device identity, billing, model, or protocol envelope.
- Automatically create, resume, switch, or end an interview.
- Change the separate public-homepage or guide footer actions.
- Add new persistence, telemetry, audio, transcript, or screenshot handling.

## Decisions

### Restore the previously approved transparent visual family

Use the text-free shield/microphone/check artwork with a real PNG alpha channel as the single visual source family. Produce a 1024×1024 packaging asset and a size-appropriate renderer asset, then regenerate platform containers during the release build.

Alternative considered: retain the white image and rely on CSS `border-radius`. Rejected because CSS cannot affect Finder, Dock, Launchpad, installer, taskbar, or executable icons, and opaque corner pixels remain square outside the renderer.

### Validate image semantics rather than only exact hashes

Tests will require RGBA/alpha-capable PNG metadata, transparent corner pixels, expected dimensions, and configured use by macOS and Windows packaging. Release verification will inspect the generated `.icns`/`.ico` or packaged app resources in addition to source hashes.

Alternative considered: pin only a SHA-256. Rejected because the current regression was itself protected by hashes; a hash proves identity, not that the image satisfies transparent-corner behavior.

### Open the configured Web workspace without session-derived routing

The connection action will use the normalized `webWorkspaceUrl` and its existing local-development fallbacks. It will not read `activeBinding.sessionId` to create a live route. Binding state can continue to drive the status light, but not the navigation target. The visible label will describe opening OfferSteady/the Web workspace rather than entering the current interview.

Alternative considered: open the public root `/`. Rejected because the configured production URL is already `/app`, which is the authenticated product workspace users need. The existing footer action continues to provide explicit public-home navigation.

### Keep the change patch-scoped across all supported packages

Set the desktop version to 1.2.4 and build all three supported artifacts from the same renderer/package source. Signing, notarization, architecture, checksum, and download-manifest checks remain release gates.

### Remove avoidable live-entry waits

Use a short binding poll while the companion is online and waiting for a Web action, and keep the existing failure backoff. Starting a live session schedules both ASR channels concurrently but does not hold the user-facing start response for the full prewarm timeout; the first real frame remains an authoritative readiness signal.

Alternative considered: keep the ten-second idle poll and show a spinner. Rejected because it preserves the underlying cold-start delay. Alternative: remove prewarm. Rejected because background prewarm still reduces first-provider latency.

### Bound system turns without discarding partial text

Reduce the commercial system-audio maximum turn from 12 seconds to a smaller bounded interval while retaining 100 ms interim eligibility and segment identity/revision behavior. Continue using the 500 ms silence endpoint, but record `lastMeaningfulSpeechToPublishMs` separately from the existing final-frame timing so acceptance reflects what the user perceives.

Alternative considered: reduce silence to an extremely aggressive value. Rejected because meeting audio contains natural intra-sentence pauses and would fragment questions. A shorter maximum turn is safer because partial revisions already preserve growing text.

### Treat recovery as a first-class state transition

When a source resumes producing/ACKing frames, explicitly clear prior transport error and reconnect fields. Backend SSE updates triggered by device status carry refreshed runtime health, and the Web diagnosis action requests a fresh snapshot/runtime before changing the banner.

Alternative considered: hide all degraded banners after a timer. Rejected because real permission or capture failures must remain visible.

### Keep permission recovery out of the fixed audio row layout

The microphone and computer-output rows retain their accepted titles, subtitles and status labels in every capture state. A denied macOS system-audio permission remains available to diagnostics and the existing permission-check flow, but it does not inject an inline “开启电脑音频权限” button into the selector row. This prevents a path-dependent permission result from changing the window layout while leaving capture, capability reporting and system-settings integration intact.

## Risks / Trade-offs

- [macOS caches icons by bundle identity] → Verify the packaged asset directly and test a clean install; document that Finder/Dock cache may require restarting Dock or reinstalling when testing over 1.2.3.
- [A transparent asset can become illegible at 16–32 px] → Inspect generated small-size representations and retain the simplified text-free core mark.
- [Users accustomed to the direct deep link need one additional Web click] → Use a clear workspace action label and keep binding/status information visible in the companion.
- [Local fallback selection could accidentally reach a live route] → Remove session-derived candidates entirely and test every configured and local fallback candidate.
- [Shorter system turns increase commit frequency] → Keep provider connections reusable, preserve overlap/revision identity, and regression-test continuity across forced boundaries.
- [More frequent waiting-state polling adds traffic] → Scope the short cadence to registered companions waiting for a binding/live transition and retain backoff on failures.
- [Runtime refresh work can burden the event stream] → Recompute only for health-affecting events and keep transcript updates delta-only.

## Migration Plan

1. Replace source icons and semantic regressions, then generate platform icon containers.
2. Change and test the connection action target/label without touching binding or capture state.
3. Increment to 1.2.4; run desktop tests, typecheck, renderer/main builds, and OpenSpec validation.
4. Build and verify macOS arm64, macOS x64, and Windows x64 artifacts; verify architecture, identity, notarization/signing truth, icon resources, and checksums.
5. Publish the synchronized release manifest and retain 1.2.3 artifacts for rollback.

Rollback restores the 1.2.3 manifest/artifacts; no server or data migration is required.

## Open Questions

None. The requested website target is the configured OfferSteady workspace root (`/app`), not the public homepage and not a session-specific live route.
