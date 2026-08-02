# Design: Admin-managed billing catalog

## Source of truth

`billing_catalog_products` is the source of truth. Public and authenticated billing state read published products from it. A deterministic fallback with identical tiers remains for isolated tests.

## Fixed benefits

Product identifiers, kinds, point quantities, durations, and knowledge-index allowances are seeded by migration and are not accepted by the update API. The admin API updates only `display_name`, `price_cents`, and `published`.

## Versioning and orders

Every successful change receives a new monotonically increasing catalog version. Checkout creation stores a full product snapshot and amount, so later changes cannot alter pending or historical orders.

## Administration safety

Changes require `catalog.manage`, recent SMS authentication, explicit confirmation, a reason, an idempotency key, and an audit event. Only finance and super-admin roles receive this permission.

## Initial prices

The migration supplies editable launch defaults so all tiers are immediately usable. Administrators can change them without a deployment.
