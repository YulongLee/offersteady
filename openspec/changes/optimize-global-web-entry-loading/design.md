## Context

The released Global candidate has a monolithic `App.tsx`: public routes, password auth, `PrototypeProvider`, preparation, and live interview code share one eager entry. All routes wait on backend business state. The static homepage also requests video posters/metadata before React loads. Global `src` matches the released candidate except generated copy/download manifests; these generated differences must not overwrite current release downloads.

## Goals / Non-Goals

**Goals:** Keep the English appearance and all existing workflows while removing workspace/API/media dependencies from public first render. Add reproducible local tests and bundle evidence.

**Non-Goals:** CDN/DNS changes, non-Web production changes, new dependencies, backend optimization, pricing/auth protocol changes, desktop updates, or redesign. No guaranteed end-to-end latency until measured on the target user networks.

## Decisions

1. Extract the existing workspace into a lazy route module. Keep business state and existing protected routing there. Public layout/homepage and login use small independent modules. Shared branding and loading UI are lightweight, not imported through the workspace. Avoid barrel re-exports that pull the workspace back into the eager entry. Use eager aliases only in component tests, plus real production-build checks to prove splitting.
2. Public navigation may use a stored-session hint but never treats it as authorization. Login can restore an existing session in the background without blocking the form. Successful authentication hands off to the protected workspace, which loads authoritative state. Cancel stale restore work on unmount/new login to prevent races; never render another account's state. No anonymous `/web/state` request is required just to view public pages or redirect an unsigned visitor.
3. Keep the existing stylesheet initially, prioritizing removal of the much larger workspace script and business-state waterfall. Further CSS surgery is deferred to avoid visual regressions.
4. Promotional media uses an intersection observer for posters and an accessible explicit play action for sources. Reserve the existing aspect ratio. Browsers without the observer still offer an operable play action. Static HTML contains a non-fetching video link/fallback rather than eager poster/source attributes, so optimizing React alone cannot be undone by the parser. Do not regenerate or AI-edit the existing bitmap assets.
5. Existing gzip and immutable hashed-asset caching are already enabled and remain unchanged. CDN is a separate later configuration decision. Keep public route-specific SEO HTML and noindex/protected loading-shell boundaries.

## Risks / Trade-offs

- Lazy chunks can fail → expose a bounded reload/retry state; keep the normal current-version refresh mechanism and preserve old hashed assets at any later deployment.
- Session restore can race a new login → abort/ignore stale results and test an expired stored session plus successful login handoff.
- Moved components can change route behavior → retain routes/props and run Global regression coverage including language, commerce, media, and practice features.
- Media loading is delayed until user intent → preserve descriptions, dimensions, keyboard access, and playback controls; test click-to-play and fallback behavior.
- Local network is not representative of overseas users → report actual build/request changes, not fabricated production speedups.

## Migration Plan

Local source changes and a Global-only build; no migrations. The user explicitly authorized Global deployment on 2026-09-29 after local verification. The deployment must use the current Global production baseline, preserve its generated downloads, commercial configuration, runtime settings and old hashed assets, and retain the prior Web image for rollback. Check ordinary/mock interviews and active runtime work immediately before replacing only Web; do not restart Backend, Admin, workers, PostgreSQL, Redis or host Nginx. Verify health, build identity, assets, protected routes, and unchanged non-Web container IDs after deployment.

## Open Questions

None blocking local implementation. CDN provider, cost, and target-region validation remain separate decisions.
