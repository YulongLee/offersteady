## Context

`apps/web-global` began as an isolated snapshot of the validated Chinese Web. It localises inherited JSX text at build time by hashing Chinese source strings into `global-copy.generated.ts`. Exact entries work, but unknown strings are currently converted by broad keyword categories or a generic fallback. On the signed-in home page this maps unrelated labels, counts, descriptions, and empty states to the same long sentences. The desktop sidebar also collapses at 1050px based on the Chinese label widths, causing English navigation to lose context earlier than necessary.

The current Backend contracts and user data are healthy. This is a Global presentation defect and must remain isolated from the Chinese application and realtime interview behavior.

## Goals / Non-Goals

**Goals:**

- Give the Global workbench concise, native English navigation and dashboard copy.
- Preserve a clear hierarchy: page purpose and primary action, active/empty state, recent sessions, material readiness.
- Keep English navigation readable at common desktop, tablet, zoomed, and mobile widths.
- Detect fallback-copy leakage into high-visibility workbench UI during automated tests.

**Non-Goals:**

- Redesigning live interview, preparation, billing, material management, or public marketing flows.
- Changing Backend APIs, stored data, session behavior, credit rules, or authentication.
- Changing the Chinese Web or Admin appearance.

## Decisions

### Use explicit English source for the workbench shell and home pages

The Global app will own concise English strings for navigation, account labels, interview home, written-exam home, empty states, recent-session headings, and readiness summaries. Explicit copy is preferred over adding more broad keyword categories because component context determines the correct wording and length.

Alternative considered: keep category-based translation and shorten every fallback. This would still map unrelated labels to identical text and allow future source changes to silently corrupt layout.

### Make unresolved translation visible to tests but neutral in production

The copy generator will retain deterministic coverage, but generic fallback prose must not appear in the workbench. Tests will assert that the rendered workbench contains neither Han characters nor known generic fallback sentences. The broader catalogue migration can continue incrementally outside this bounded fix.

Alternative considered: remove the translation runtime from the entire Global app now. That is a much larger migration and would risk unrelated feature coverage.

### Tune the existing design system instead of introducing a new visual language

The workbench will retain the current dark palette, typography, borders, radii, and green accent. Layout changes will widen the desktop sidebar, use a shorter readable page heading, reduce oversized empty space, and improve dashboard card proportions. The existing bottom navigation remains the mobile pattern.

Alternative considered: introduce a new component library or dashboard design. That expands bundle size and visual scope without addressing the root cause.

## Risks / Trade-offs

- [Explicit copy diverges from the Chinese source structure] → Keep changes in `apps/web-global` and cover route actions in Global tests.
- [Other Global routes still contain broad fallback copy] → Scope this fix to the signed-in shell and home surfaces, then audit remaining routes separately.
- [Wider sidebar reduces content width on small laptops] → Collapse to the compact icon rail only below the measured breakpoint and keep the existing mobile bottom navigation.
- [Visual checks are limited because the browser capture surface is unavailable] → Add DOM/copy and production-build checks now, then perform a visual acceptance pass from the deployed preview before expanding the redesign.

## Migration Plan

1. Add explicit workbench copy and scoped CSS without changing routes or data operations.
2. Run Global component tests, copy audit, typecheck, and production build.
3. Deploy only the isolated Global Web image and confirm public health plus route availability.
4. Retain `global-email-auth-20260904.1` as the immediate rollback release.

## Open Questions
September 7 owner-approved follow-up: include Resume/JD empty-state and add-dialog English presentation. The production source still interpolated Chinese category names into English text; local correction was not in the deployed file. Overlay LibraryManager only, keeping all upload/parse operations intact and verify actual deployed chunk strings. User-authored filenames and content are not translated.

- Should the remaining preparation, materials, billing, and settings routes receive the same explicit-copy migration in a separate pass after this workbench is accepted?
