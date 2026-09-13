## ADDED Requirements

### Requirement: Public startup excludes the live workspace
The Chinese Web SHALL load the live workspace only when needed and SHALL preserve existing public HTML, canonical URLs, metadata and sitemap.

#### Scenario: Anonymous homepage load
- **WHEN** a production-mode homepage build is inspected
- **THEN** its transitive synchronous imports exclude LivePage, ConversationMonitor and the math renderer, and its initial HTML still contains the approved product heading and text

#### Scenario: Preparation warms the live route
- **WHEN** the preparation page mounts
- **THEN** it starts optional module warm-up without starting audio, an answer or a new session, and a failed warm-up does not prevent preparation

### Requirement: Existing budgets remain enforced
The build SHALL keep the 410,000-byte public-entry and 1,350,000-byte total-JS ceilings and SHALL report actual outputs without excluding business chunks from totals.

#### Scenario: Build verification
- **WHEN** the production candidate is built
- **THEN** the existing budget verifier runs unchanged and the result is reported, including any unresolved failure

### Requirement: Regression tests protect the approved product
Tests SHALL preserve existing login, membership, billing, materials, live answers and screenshot behavior, and SHALL validate the approved homepage rather than obsolete promotional claims.

#### Scenario: Current homepage and partner navigation
- **WHEN** homepage and partner tests execute
- **THEN** four value cards, truthful configuration-driven pricing, expandable platform/FAQ details and permanent navigation are checked, and paused activity still prevents joining

#### Scenario: Deletion service failure
- **WHEN** a synthetic material deletion is explicitly mocked to fail with a network error
- **THEN** the error remains visible and the material remains present without making a real deletion request

#### Scenario: Live navigation and interaction
- **WHEN** a synthetic authorized user enters the real lazy route
- **THEN** its workspace resolves using the same account context and existing interaction regressions remain passing

### Requirement: Explicitly authorized verification and handoff
The initial implementation SHALL remain local until a separate explicit deployment request. An authorized CN publication SHALL exclude international services, backend behavior, credentials and real-user data changes.

#### Scenario: Completion report
- **WHEN** the work is handed off
- **THEN** it includes measured before/after sizes, actual test/build results, a local preview and scoped changes, without asserting production deployment or real-user latency gains

#### Scenario: Subsequently authorized CN publication
- **WHEN** the user explicitly authorizes CN deployment after reviewing the local handoff
- **THEN** the reviewed allowlist is rebased on current production source, prices are rebuilt and checked live, old assets and rollback backups are preserved, production HTML is verified with normal and Baiduspider UAs, and unresolved budget failures are reported without changing thresholds
