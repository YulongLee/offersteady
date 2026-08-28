# Release 1.2.5 Local Acceptance

Release 1.2.5 is a local macOS Apple Silicon acceptance candidate for privacy-safe preparation warmup, warmed media-source promotion, faster source-aware terminalization, bounded visible confirmation, and content-free stage diagnostics. It preserves the 1.2.4 companion layout, approved transparent icon, product name, bundle identifier `com.offersteady.companion`, production endpoint defaults, and realtime protocol 2.0 compatibility.

## Implemented Scope

- Transfer healthy microphone and system-audio streams from preparation monitoring to the live publisher without reopening them.
- Reopen only a stale transferred source while allowing the healthy source to proceed independently.
- Schedule both ASR channels during authoritative preparing-session binding without publishing audio, creating publishers, transcribing, or starting realtime billing.
- Use a 350 ms system-audio tail and a 480 ms microphone tail while retaining residual-noise release, maximum-turn bounds, and one terminal per generation.
- Keep provisional transcript text visible and bound `正在确认` to 1.5 seconds without allowing late older events to overwrite newer content.
- Add content-free warm-start and terminal-stage timing fields and performance distributions.

## Verification

- Node workspace tests: 95 files and 613 tests passed.
- Backend tests: 339 passed, 14 skipped; the only warning is the existing Starlette/httpx deprecation warning.
- All workspace TypeScript checks passed.
- Desktop, protocol, admin, API, and guarded production Web builds passed.
- Python application compilation passed.
- `openspec validate prewarm-and-accelerate-realtime-1-2-5 --strict` passed.
- No Prompt or AI behavior changed, so no AI eval fixture change was required.

## Apple Silicon Artifact

- Application version/build: `1.2.5` / `1.2.5`.
- Bundle identifier: `com.offersteady.companion`.
- Main executable and native capture runtime: arm64.
- Code signature: `Developer ID Application: Yulong li (8Y5FAR3TF3)`; deep strict verification passed.
- Local ZIP: `apps/desktop/release/OfferSteady-Companion-1.2.5-macOS-arm64.zip`.
- ZIP SHA-256: `dfdc21c51ec2ebcbffee0f47837c36a4cbaacc27b0a8c03524e66e7abe080fda`.
- This local package is Developer-ID signed but not notarized; notarized DMG publication and production Backend/Web deployment require separate authorization.

The installed 1.2.4 application was moved intact to `/Applications/OfferSteady Rollbacks/面试稳伴随程序-1.2.4-before-1.2.5.app`. The local 1.2.5 application is installed at `/Applications/面试稳伴随程序.app` and was launched for physical acceptance.
