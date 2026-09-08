# Global customer route and copy inventory

This inventory supports OpenSpec change `complete-global-english-product-experience`. It covers product-authored Global Web chrome; user materials, transcripts, and generated answers are runtime content and are intentionally not translated by the UI catalogue.

## Route families

| Family | Routes | Critical states |
| --- | --- | --- |
| Public and account | `/`, `/login`, `/guide`, `/terms`, `/privacy` | signed out, code requested, validation error, loading, legal/help content |
| Legacy invitation | `/invite/:code` | unconditional safe redirect to `/`; no referral resolution or activation |
| Interview workbench | `/app`, `/app/interviews/new`, `/app/interviews/:id/prepare`, `/app/interviews/:id/live`, `/app/interviews/:id/review` | empty/populated, create error, device pairing, preparing, live/reconnecting, answer streaming, completion/review |
| Written exams | `/app/written-exams`, `/app/written-exams/new`, shared prepare/live/review routes | empty/populated, pairing, screenshot processing, answer streaming, completion/review |
| Materials | `/app/library` | empty/populated per type, upload, indexing quote, processing, ready, failed, rename, reprocess, delete |
| Account utilities | `/app/billing`, `/app/devices`, `/app/settings`, `/app/guide` | balance/pass/ledger, empty activity, release availability, preferences, help/search |

## Copy baseline

- 838 distinct Chinese product/operational source literals are currently discovered by the Global copy generator after referral and domestic billing presentation were removed from the active bundle.
- Every discovered literal has an explicit catalogue entry; missing entries fail generation with file and line information.
- The previous category-level fallback sentences are forbidden by the copy audit.
- The largest source concentrations are `App.tsx`, `LibraryManager.tsx`, and shared answer/conversation components. Inactive domestic-only source modules remain in the repository for comparison but are not imported by the Global route bundle.

## Responsive coverage

The supported structure classes are desktop (`>1050px`), compact desktop/tablet (`721–1050px`), and narrow/mobile (`<=720px`). Verification covers shell/navigation, page headers, panels/forms, live workspace, materials, billing, dialogs, tables/lists, and fixed mobile controls. A real-browser visual pass remains required before deployment approval.

