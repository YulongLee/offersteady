## Why

The authenticated workbench currently offers an internal usage guide but no direct route to the externally maintained product manual. A stable “用户手册” navigation entry lets users reach the latest Feishu-maintained documentation without requiring a Web release for every manual update.

## What Changes

- Add a “用户手册” entry to the authenticated workbench navigation.
- Open the configured Feishu Drive folder in a new browser tab so the current interview workspace remains available.
- Apply safe external-link attributes and expose the same destination in desktop and mobile workbench navigation.
- Keep the existing internal “使用说明” route unchanged.

## Capabilities

### New Capabilities

- `external-user-manual-navigation`: Defines the authenticated workbench entry and safe navigation behavior for the externally maintained user manual.

### Modified Capabilities

None.

## Impact

- Web application navigation and its focused tests.
- Responsive workbench navigation column count.
- No Backend API, database, desktop companion, authentication, or sensitive-data handling changes.
