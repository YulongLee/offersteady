# Change: Add admin-managed billing catalog

## Why

The server-owned billing catalog is still hardcoded, so pricing changes require a release and the point packs do not match the approved commercial tiers.

## What Changes

- Persist the commercial product catalog in PostgreSQL.
- Fix time-pass benefits at 1, 3, 7, 15, and 30 days.
- Fix point-pack benefits at 1,000, 3,000, 10,000, 30,000, and 66,666 points.
- Allow authorized finance administrators to change display names, prices, and publication state.
- Keep benefit quantities immutable from the administration API.
- Continue snapshotting product and amount data into each checkout order.

## Non-goals

- Changing payment providers or callback behavior.
- Allowing arbitrary benefit quantities to be created from the admin console.
- Repricing previously created orders.

## Capabilities

- `admin-managed-billing-catalog`: Durable catalog configuration and controlled administration.
