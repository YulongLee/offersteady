## ADDED Requirements

### Requirement: Preserve Global behavior while applying scoped reads
Global SHALL use owner indexes for binding/account lists and a canonical owner/session getter for single termination, with no global hit-path scan, preserving precision/order/retirement/TTL/initialization and Global events, permissions, languages, membership/Creem and1.5second status cache. Only reviewed function nodes may change.

#### Scenario: History and index lifecycle
- **WHEN** unrelated synthetic history grows through1, an online-sized population and10000, with clear/rebind/restart/expiry/corruption interleavings
- **THEN** owner hit-path client/server work is bounded by own results with zero global HVALS/HGETALL/HSCAN; canonical state remains authoritative and incomplete metadata fails closed

### Requirement: Bound cleanup and separate preparation without changing billing
Global SHALL add independent bounded preparation and optional old-object physical close while preserving authoritative session/billing state, retirement before close, late-result rejection, original gateway fallback and Global closure-failure counters. Accepted close jobs MUST drain once, never target replacements or expand without bound.

#### Scenario: Slow close, cancel or submit failure
- **WHEN** lifecycle workers are slow, the close queue is full, a source reconnects, submission fails after enqueue or publisher creation is cancelled
- **THEN** preparation can progress in its own2+8 capacity, fallback cleanup completes, old jobs only close captured objects once and abandoned creation compensates once

### Requirement: Lightweight acknowledgements preserve authority
Global SHALL use an optional authoritative control projection for content-free ACKs, retain original cache locks/TTL/cross-owner rejection and fallback, and skip unused DEBUG serialization at INFO without changing fields/frequency or product functions.

#### Scenario: ACK stages and compatibility
- **WHEN** all ACK stages, missing/foreign sessions or legacy repositories are exercised
- **THEN** original wire/error/cache contracts remain and valid projection paths load no bound materials
