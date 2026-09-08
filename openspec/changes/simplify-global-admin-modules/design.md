## Context

The same React Admin source builds two editions. Its current navigation array is mostly shared, so the Global build exposes China-specific operational screens even though Global commerce is isolated behind Creem. Backend APIs are also shared and must remain available to the Chinese Admin.

## Goals / Non-Goals

**Goals:**

- Produce a focused Global navigation containing only applicable operational modules.
- Keep view selection and permission fallback deterministic after the scope reduction.
- Preserve the complete Chinese Admin navigation and all Backend capabilities.

**Non-Goals:**

- Deleting shared React components or Backend endpoints used by Chinese production.
- Changing permissions, administrator authentication, payment activation, or customer-facing behavior.
- Enabling Creem checkout.

## Decisions

- Define separate `globalViews` and `chinaViews` lists and select the active list from the existing compile-time edition flag. This is clearer and safer than scattering per-item predicates throughout rendering.
- Keep Global order and subscription operations inside `GlobalCommercePanel`; the shared `orders` screen remains a domestic billing screen and is excluded from Global navigation.
- Retain unused shared component source because the same application source builds Chinese Admin. The Global production minifier can eliminate unreachable view branches where possible, while source deletion would break domestic behavior.
- Add a pure exported view-selection helper so tests can verify both editions without rebuilding or changing runtime environment globals.

## Risks / Trade-offs

- [A stale selected view could become unavailable] → Resolve the current view against the edition-specific list and fall back to the first permitted Global view.
- [Shared code remains in the repository] → This is intentional edition isolation; user-facing removal is enforced in the generated Global navigation.
- [A future Global module may be added to the shared list accidentally] → Regression tests assert the exact Global and Chinese module identifiers.

## Migration Plan

Build and test both Admin editions, deploy only the overseas Admin image, and verify the visible navigation after authenticated access. Retain the previous Global Admin image for immediate rollback. No database migration is required.

## Open Questions

None.
