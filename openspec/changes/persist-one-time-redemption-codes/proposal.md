## Why

Production redemption codes are currently marked as used only in backend process memory, so a restart can make a previously consumed code usable again and can hide its credited ledger entry. The first public test release needs durable, globally one-time redemption semantics before more codes are distributed.

## What Changes

- Persist configured redemption-code inventory, redemption ownership, idempotency records, and redemption-credit ledger entries in PostgreSQL.
- Store only keyed code digests and masked hints in PostgreSQL; keep plaintext codes in server-side configuration.
- Serialize redemption with database locks so concurrent requests can credit a code only once.
- Merge durable redemption credits into the existing billing state without changing the Web API or redemption UI.
- Keep built-in synthetic/demo behavior and database-free development tests available.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `points-redemption-codes`: Clarify durable restart behavior, digest-only storage, atomic global use, and persisted wallet history for production codes.

## Impact

- Backend billing dependency construction and balance calculation.
- A new PostgreSQL migration and points-redemption repository.
- Production configuration gains an independent redemption-code digest pepper.
- No breaking HTTP or frontend contract changes.
