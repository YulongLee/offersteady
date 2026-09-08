## Why

The deployed Global workbench renders repeated generic fallback translations in navigation, headings, empty states, and material summaries. Those long strings overflow compact components and make the signed-in product look broken, especially at desktop widths where the sidebar collapses before the English labels can fit.

## What Changes

- Replace fallback-generated copy on the Global interview and written-exam home surfaces with concise, context-specific English product copy.
- Make the Global desktop workbench sidebar and dashboard responsive to English label lengths without changing the validated Chinese application.
- Simplify the empty home state and dashboard hierarchy so the primary action, recent sessions, and material readiness are immediately understandable.
- Add copy and responsive-layout regression checks that prevent generic fallback text or unreadable navigation from returning to these high-visibility surfaces.

## Capabilities

### New Capabilities

- `global-workbench-experience`: Defines the readable, responsive, English-only signed-in home experience for the independently deployed Global product.

### Modified Capabilities

None.

## Impact

- Affects only `apps/web-global`, its generated English catalogue, styles, and Global Web tests.
- Does not change Backend APIs, authentication behavior, interview processing, the desktop companion, the Chinese Web, or the Chinese administration application.
- Deployment remains isolated to `offersteady.com` and retains the existing Global rollback release.
