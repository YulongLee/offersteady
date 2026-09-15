## Why

When visitors open the international workspace route (`/app`), the browser first paints the SEO-friendly marketing markup embedded in the shared HTML shell. After JavaScript and authentication state load, React replaces it with the workspace. This creates a visible flash of the wrong page and makes slow connections feel like a navigation failure.

## What Changes

- Keep the existing marketing/SEO prerender for the public landing route and indexable content pages.
- Add an application-entry shell for `/app` that presents a neutral workspace loading state before React mounts.
- Ensure the shell is replaced cleanly when the React application is ready, including the existing authenticated and unauthenticated flows.
- Add regression coverage proving `/app` does not expose marketing copy before the application mounts while `/` remains indexable.

## Capabilities

### New Capabilities

- `global-app-entry-shell`: Provide a route-appropriate loading shell for the international workspace entry without changing the public landing-page design.

### Modified Capabilities

- None.

## Impact

- `apps/web-global/index.html` and early client bootstrapping styles/script.
- `apps/web-global/src/main.tsx` or related app bootstrap code for removing the entry shell after mount.
- International web build and route-shell regression tests.
- No backend, API, database, model, or user-data behavior changes.
