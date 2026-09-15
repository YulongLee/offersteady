## Context

The global admin panel currently models both Creem Test and Live as selectable environments. The approved international product is intended to collect production payments only, while the backend still defaults to `test` and validates activation against both modes. The change must be isolated to the global edition and must not delete existing commerce records.

## Goals / Non-Goals

**Goals:**

- Present one unambiguous Live configuration in the global admin UI.
- Make provider reads, mapping validation, activation, checkout, and webhook handling use Live credentials/products.
- Fail closed when required Live configuration is incomplete.
- Preserve existing orders, entitlements, audit records, and domestic payment behavior.

**Non-Goals:**

- No changes to the domestic edition.
- No deletion of Test credentials or historical records in this change.
- No live payment/order creation as part of automated tests.

## Decisions

- **Single fixed provider mode for global commerce:** global services use `live` directly; the UI and public API do not expose a mode selector. This is safer than hiding a selector while continuing to honor arbitrary mode query parameters.
- **Reject Test-mode requests:** admin endpoints receiving `mode=test` return a clear conflict/unsupported response for global commerce. This prevents stale clients from silently modifying Test state. Existing Test rows remain untouched for rollback/audit.
- **Live-only readiness gate:** activation checks Live credentials, Webhook Secret, active USD product mappings, public/legal URLs, and the global master switch. The existing atomic disable of the other mode is retained as a defensive migration step.
- **UI copy and tests:** replace Test/Live tabs with a single “Live 正式” panel and update API client calls/tests to assert no Test controls are rendered.

## Risks / Trade-offs

- [Risk] Existing operators may have saved only Test mappings → [Mitigation] show an explicit Live setup checklist and keep checkout disabled until all Live mappings validate.
- [Risk] Old clients may call Test query parameters → [Mitigation] return a deterministic unsupported-mode error and log an audit event without changing data.
- [Risk] Removing Test controls can slow debugging → [Mitigation] retain server-side redacted diagnostics and rollback to the previous release if Live validation fails.

## Migration Plan

1. Deploy code with Live-only UI/API behavior while leaving existing records intact.
2. Configure and validate Live credentials, webhook secret, and four active product mappings.
3. Enable the global commerce master switch and Live provider through the admin panel.
4. Verify catalogue, checkout creation (without completing a real order), webhook signature handling, and order status reads.
5. Roll back application release if validation fails; do not drop database or Redis volumes.

## Open Questions

- Whether Test credential rows should be archived in a later maintenance migration after a successful Live launch.
