## Context
The existing public /api/v1/web/downloads/desktop/{filename} route resolves the Global manifest and redirects to a short-lived storage URL. Homepage should not load authenticated application state.
## Goals / Non-Goals
Offer login-free platform downloads beneath existing hero actions. Do not change backend, Companion packages, authentication, payments or China.
## Decisions
Generate a small public JSON catalogue and static homepage links at build time from the canonical Global desktop release manifest. Include only published, non-development entries with valid checksums and Global filenames. Browser and initial HTML reuse generated metadata. Backend remains authoritative for withdrawal and storage URLs; no signed URLs or object keys enter the bundle. Use native details/summary for macOS selection and understated outlined buttons. Owner revision: show buttons only, with just Apple Silicon / Intel labels in the Mac selector. Remove helper copy and the three hero trust-list labels. Signing metadata is unchanged; no signing claims are made.
## Risks / Trade-offs
Manifest updates require a Web rebuild to update homepage metadata. Existing backend rejects withdrawn releases immediately. Failed manifest generation fails the build, never falls back to Chinese packages. Public release links are checked before cutover. No additional homepage API request.
## Migration Plan
Overlay only scoped Web/build files on current Global baseline, using that release's manifest. Verify tests, build, mobile and desktop; retain prior image. Deploy only Web after idle checks; verify unchanged core services.
## Open Questions
None. User approved the design and deployment.
