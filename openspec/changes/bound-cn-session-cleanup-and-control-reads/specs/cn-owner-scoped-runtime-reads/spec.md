## ADDED Requirements

### Requirement: Session and owner reads remain scoped
CN SHALL terminate one session using its canonical owner/session binding and SHALL list user bindings/accounts from owner indexes without scanning unrelated global history on a valid indexed read. Original ownership, ordering, stale state, precision, generation, retirement and legacy fallback contracts MUST remain.

#### Scenario: Unrelated history scales
- **WHEN** 1, 1242 and 10000 synthetic histories coexist with one target owner/session
- **THEN** target read transport/decoding and server work remain bounded to the target owner records, with zero global HVALS/HGETALL/HSCAN on the hit path

### Requirement: Atomic index migration and lifecycle
Indexes SHALL be atomically seeded during initialization after legacy seed and updated with canonical writes, retain shared TTL semantics and fail closed if incomplete or corrupt; they MUST NOT extend user material retention or silently omit authorized history.

#### Scenario: Restart or concurrent seed and clear
- **WHEN** migrated records, new writes, clear, rebind and restart interleave
- **THEN** indexed reads see authorized current canonical state, retired sessions remain stale and other owners' records never leak

#### Scenario: TTL and integrity
- **WHEN** unrelated active traffic extends canonical lifetime or index metadata expires/corrupts
- **THEN** valid indexes cover existing records; absent integrity proof raises an error instead of scanning globally or returning a partial list

#### Scenario: Complete expiry and old writer restart
- **WHEN** both canonical hashes and metadata fully expire, or a new repository starts after an idle rollback writer
- **THEN** a completely expired runtime reads empty and accepts fresh indexed writes; initialization atomically rebuilds from canonical state even if an old ready marker remains
