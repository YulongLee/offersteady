## 1. Global Web state coordinator

- [x] 1.1 Add public/authenticated in-flight coalescing and a short success-only cache to the Web adapter.
- [x] 1.2 Add forced-refresh options at authoritative Global Web callers and preserve abort/clone behavior.

## 2. Regression coverage

- [x] 2.1 Add focused regressions for state coalescing, cache isolation/expiry/failure/abort, forced refresh, and preservation of five-second transcript sampling.

## 3. Verification and release readiness

- [x] 3.1 Run focused Global Web tests, full Global Web tests, typecheck, production build, strict OpenSpec validation, and `git diff --check`.
- [x] 3.2 Verify the Global overlay is limited to the approved Web runtime/test files plus the additive protocol type alignment, and record that production deployment remains pending.

## Verification notes (2026-10-14)

- Global Web focused regression: 21 passed; full Global Web suite: 184 passed.
- Global Web typecheck and production build passed locally.
- `openspec validate sync-global-web-performance --strict` and `git diff --check` passed.
- Candidate source was copied from `/opt/offersteady-global/current` into `/opt/offersteady-global/releases/20261014-global-web-performance-1`. The overlay changed only `apps/web-global/src/backend-adapter.ts`, `apps/web-global/src/WorkspaceApp.tsx`, `apps/web-global/src/LibraryManager.tsx`, `apps/web-global/src/domain.ts`, and the additive `packages/protocol/src/context.ts` declarations; the release environment only changed the candidate version markers.
- Candidate Global Web image built successfully after the type-only protocol alignment. Isolated container checks for `/`, `/login`, `/app`, `/healthz`, `/api/v1/web/state`, and the production Global manifest all passed.
- Global production deployment remains pending; no running Global container was recreated.
