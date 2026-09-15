## Context

The international web app uses one static `index.html` for both public routes and the React workspace. The static body contains marketing content so crawlers and users without JavaScript can understand the product. Nginx serves that same document for `/app`, therefore the browser paints the marketing content before React has mounted and before authentication/state bootstrap completes.

## Goals / Non-Goals

**Goals:**

- Eliminate the marketing-page flash on `/app` and its nested workspace routes.
- Preserve the current public homepage appearance, copy, metadata, and crawlability at `/` and public content routes.
- Keep the change client-side and reversible, with no changes to authentication or interview behavior.
- Provide an honest progress cue while the app restores the session and loads initial state.

**Non-Goals:**

- Redesigning the workspace or public homepage.
- Changing route authorization, API contracts, or loading duration.
- Hiding indexable content from crawlers on public routes.

## Decisions

1. **Route-aware pre-mount shell in the existing document.** Add a small inline boot script before the module entry point. It detects `/app` paths and marks the document as an app entry before first paint. CSS hides the SEO prerender only for those paths and shows a compact workspace loading shell. This avoids a second HTML document and keeps the deployment contract unchanged.

2. **Explicit removal after React mount.** The React bootstrap removes the app-entry marker and shell once `createRoot(...).render(...)` has been scheduled. Existing `RouteLoadingPage` remains responsible for state/auth loading, so the visual transition is continuous rather than a blank frame.

3. **Public routes remain untouched.** The boot script does not mark `/`, `/features`, `/pricing`, `/download`, or other public routes. Their current prerendered marketing markup remains visible and indexable.

4. **Regression tests at source/build level.** Add tests for the route detector and HTML contract, plus run the global web typecheck/build. No new dependency is needed.

## Risks / Trade-offs

- [Risk] If JavaScript fails entirely, `/app` shows a loading shell instead of marketing copy. → Mitigation: include a clear “Reload to continue” fallback link and keep all public routes unchanged.
- [Risk] A cached document could briefly use an old shell. → Mitigation: keep the existing no-store behavior for `/app` and make the boot script self-contained in `index.html`.
- [Risk] The shell may differ slightly from the final workspace styling. → Mitigation: reuse existing global colors/typography and keep it intentionally minimal; the React loading state follows immediately.
