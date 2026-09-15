## Why

Global production diagnostics showed that the Web and Backend containers were created from different release directories. Separately, the preparation page fetched a desktop binding only once and converted API failures into an apparently missing binding. Together these conditions made an online Companion look disconnected and made recovery require a manual refresh.

## What Changes

- Keep the Global preparation page synchronized with the server binding while it is open, with a single in-flight refresh and bounded cadence.
- Preserve HTTP status on API envelope errors so a genuine outage is distinguishable from a normal 404/no-binding response.
- Add a deployment guard that refuses to complete when Global Web and Backend are not created from the same Compose release directory.
- Preserve the existing pairing, realtime, screenshot, audio, billing and session contracts.

## Capabilities

### New Capabilities

- `global-companion-web-sync`: The preparation page reflects binding changes without manual refresh and surfaces actual API failures.
- `global-release-consistency`: Global application services must be released from one Compose bundle.

### Modified Capabilities

None.

## Impact

- Global Web preparation polling and API error handling.
- Global deployment verification script.
- No database migration, media persistence, payment change, or desktop protocol change.
