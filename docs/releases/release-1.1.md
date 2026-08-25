# Release 1.1

Release 1.1 establishes version `1.1.0` as the shared desktop baseline for macOS Apple Silicon, macOS Intel, and Windows x64. The macOS Bundle Identifier remains `com.offersteady.companion`, and the realtime protocol remains version `2.0`.

## Included changes

- Desktop audio stability: bounded AudioWorklet transfers, throttled display-only health updates, renderer crash recovery, capture health states, watchdog recovery, and content-free transport diagnostics.
- Realtime subtitle diagnostics: revision-level Qwen, Redis, SSE, Browser state, and React paint timestamps, gated behind explicit diagnostic enablement.
- Existing Backend/Web changes in the release branch, including persistent realtime ASR prewarming and session-minute billing from the current baseline.

## Verification

- Workspace TypeScript checks: passed.
- JavaScript/TypeScript tests: Admin 34, API 90, Desktop 97, Web 286, Protocol 31 passed.
- Backend tests: 304 passed, 14 skipped.
- Production builds: Web, Admin, and Desktop passed.
- Desktop download/publication regression tests: 7 passed.
- OpenSpec strict validation: passed for the release and directly affected changes.

## Desktop artifacts

| Target | Artifact | SHA-256 | Release integrity |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.0-macOS-arm64.dmg` | `874eb964930f194b090ec1bf43fa617c31bac13316ca3de619eac390d001d98c` | Developer ID verified, App and DMG notarization Accepted, stapler and Gatekeeper passed |
| macOS Intel | `OfferSteady-Companion-1.1.0-macOS-x64.dmg` | `29d10b33c69caaadd50c34fc7060aafe396cb6c140078938d4870d29ef628401` | Developer ID verified, App and DMG notarization Accepted, stapler and Gatekeeper passed |
| Windows x64 | `OfferSteady-Companion-Setup-1.1.0-Windows-x64.exe` | `9cff7ceb0567dc939c7667522818f61bd5c61dffc4e1405163ef82387d16112f` | NSIS structure validated; Authenticode certificate is not available, so metadata remains non-verified |

## Publication

All three artifacts are uploaded under `desktop-releases/<platform>/<architecture>/1.1.0/`. The checked-in desktop release manifest is the source used by the production Backend download API.
