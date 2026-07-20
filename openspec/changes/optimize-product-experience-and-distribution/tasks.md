## 1. Shared Contracts and Fixtures

- [x] 1.1 Define protocol types for WeChat identity state, provider binding and safe account summary
- [x] 1.2 Define knowledge collection, document version, processing status, indexing estimate and usage contracts
- [x] 1.3 Extend billable operation kinds with knowledge indexing and immutable document-version references
- [x] 1.4 Define versioned desktop release-manifest entries for platform, architecture, checksum, signing and capabilities
- [x] 1.5 Add synthetic fixtures for identity states, library lifecycle, revised catalog and three desktop artifacts
- [x] 1.6 Add protocol serialization, backward-compatibility and sensitive-field exclusion tests

## 2. Public Landing and Adaptive Home

- [x] 2.1 Replace the platform-specific hero copy with outcome-led, platform-neutral product messaging
- [x] 2.2 Build feature sections for personal context, voice/manual/screenshot input, concrete sources and cross-device use
- [x] 2.3 Add observable product examples and AI-advice/privacy boundaries for every primary marketing claim
- [x] 2.4 Drive platform availability claims from controlled release and feature flags
- [x] 2.5 Implement task-priority home headings for active, preparing, completed and empty interview states
- [x] 2.6 Implement timezone-aware secondary greetings with a neutral server/client-safe fallback
- [x] 2.7 Add landing and home tests for macOS, Windows, unreleased capabilities, timezone boundaries and hydration fallback
- [ ] 2.8 Run desktop, tablet and mobile visual, keyboard, screen-reader and contrast checks

## 3. WeChat Login and Account Safety

- [x] 3.1 Define a replaceable server-side WeChat identity-provider adapter
- [x] 3.2 Implement short-lived single-use authorization state creation and validation
- [ ] 3.3 Implement server-only authorization-code exchange with encrypted provider-subject mapping
- [x] 3.4 Implement first-login account creation and idempotent provider binding
- [ ] 3.5 Implement authenticated binding, collision detection and verified merge/recovery handoff
- [x] 3.6 Prevent removal of the last verified login or recovery method
- [ ] 3.7 Build WeChat login, loading, callback, failure and fallback states in the Web login page
- [x] 3.8 Redact codes, tokens and provider identifiers from logs, analytics and client errors
- [x] 3.9 Add tests for state mismatch, replay, expired callback, duplicate account creation, collision and unauthorized unbind
- [x] 3.10 Document required WeChat platform credentials, redirect domains, privacy disclosure and provider-mode choice

## 4. Knowledge Library CRUD

- [x] 4.1 Implement owner-scoped collection create, list, rename and idempotent delete APIs
- [x] 4.2 Implement document upload metadata, versioning and PDF/DOCX/TXT/Markdown validation
- [x] 4.3 Implement pending, processing, ready, failed, disabled and deleted document transitions
- [x] 4.4 Build the library collection list, create dialog and empty/loading/error states
- [x] 4.5 Build collection detail with add document, status, retry, replace, rename and delete actions
- [x] 4.6 Add explicit delete confirmation showing affected documents and interview selections
- [x] 4.7 Invalidate deleted or disabled documents from future selections and retrieval without automatic replacement
- [x] 4.8 Preserve only source name, version and deleted marker for historical answer provenance
- [ ] 4.9 Schedule content, parsed text and vector deletion while preserving minimal audit metadata
- [ ] 4.10 Add ownership, unsupported-file, oversize, retry, concurrent delete and historical-provenance tests

## 5. Knowledge Indexing Metering

- [x] 5.1 Implement server-side base estimate of 20 points for documents up to 5 MB and 50 pages
- [x] 5.2 Return a confirmation-required estimate for documents above the base tier
- [x] 5.3 Reserve points against a document-version idempotency key before starting parsing and indexing
- [x] 5.4 Settle exactly once after a usable index is stored and release on failure, timeout or cancellation
- [x] 5.5 Detect unchanged content and reuse its result or usage record without a second charge
- [x] 5.6 Keep document content, parsed text and embeddings out of billing and ordinary operational logs
- [x] 5.7 Show estimate, membership exclusion, projected balance and confirmation before indexing
- [x] 5.8 Preserve a non-indexed upload and offer purchase recovery when balance is insufficient
- [ ] 5.9 Add unit and concurrency tests for estimate tiers, replay, duplicate workers, failure release and insufficient balance
- [x] 5.10 Add an end-to-end synthetic journey from upload through one successful index and one ledger settlement

## 6. Pricing Catalog and Consumption Disclosure

- [x] 6.1 Publish a new catalog version with passes priced at ¥69.90, ¥129.90, ¥219.90 and ¥329.90
- [x] 6.2 Publish points packs at 300/¥39.90, 800/¥89.90 and 2000/¥199.90
- [x] 6.3 Preserve existing order product snapshots and already-granted entitlements during catalog migration
- [x] 6.4 Add ordinary answer, screenshot answer and knowledge indexing to the consumption explanation
- [x] 6.5 Show effective daily price, point unit price, included usage, exclusions and normal-use limits
- [x] 6.6 Show operation price, entitlement source and projected balance at each billable confirmation
- [x] 6.7 Keep knowledge indexing point-billed while an answer/screenshot membership is active
- [x] 6.8 Add conservative unit-cost inputs and block catalog publication below the configured margin threshold
- [x] 6.9 Add catalog, legacy-order, active-member, indexing-exclusion and margin-threshold tests
- [ ] 6.10 Run billing-page responsive, loading, failure, empty-order, member and points-user checks

## 7. Cross-Platform Download Center

- [ ] 7.1 Implement an authorized release-manifest service with publish, replace, withdraw and rollback operations
- [x] 7.2 Add macOS arm64, macOS x64 and Windows x64 build targets to the release pipeline
- [ ] 7.3 Configure macOS Developer ID signing, notarization and artifact verification
- [ ] 7.4 Configure Windows code signing, installer verification and safe uninstall metadata
- [x] 7.5 Generate file size, SHA-256, minimum OS, publication time and protocol compatibility metadata
- [x] 7.6 Build three explicit download cards with automatic recommendation and manual selection
- [x] 7.7 Add “how to check your chip/architecture” and platform-specific installation help
- [x] 7.8 Hide active download actions for unsigned, incomplete, withdrawn or incompatible artifacts
- [x] 7.9 Drive post-install capture UI from runtime capabilities rather than package labels
- [ ] 7.10 Add manifest authorization, checksum, withdrawal, wrong-architecture and capability-degradation tests
- [x] 7.11 Publish the prototype macOS arm64 artifact to OSS and expose a same-origin direct-download action with a short-lived signed redirect

## 8. Windows Companion Foundation

- [x] 8.1 Implement Windows x64 application packaging, launch and secure local credential storage
- [ ] 8.2 Implement the shared pairing, authorization, capture-state and protocol handshake on Windows
- [ ] 8.3 Add Windows microphone permission and device-selection handling
- [ ] 8.4 Implement Windows system-audio capability detection behind the existing replaceable capture adapter
- [x] 8.5 Provide truthful manual-input and screenshot recovery when Windows audio capture is unavailable
- [ ] 8.6 Add Windows 10/11 synthetic and physical-device tests for installation, upgrade, permissions and reconnect
- [ ] 8.7 Verify macOS Intel and Apple Silicon packages on physical or representative signed environments
- [x] 8.8 Document supported OS versions, known limitations, diagnostics and rollback procedures

## 9. Integration, Privacy and Release Verification

- [ ] 9.1 Reconcile this change with in-progress Web, billing, context-selection and desktop companion specs
- [x] 9.2 Verify no price, platform or login secret is trusted from client-controlled input
- [x] 9.3 Verify account, collection, document, order and release-manifest authorization boundaries
- [x] 9.4 Verify deletion retention, identity logging, document logging and payment logging policies
- [ ] 9.5 Run the new-user journey from landing through WeChat prototype login, library indexing, purchase and interview preparation
- [ ] 9.6 Run macOS arm64, macOS x64 and Windows x64 download-to-pair journeys using verified test artifacts
- [x] 9.7 Run full typecheck, unit, integration, build and OpenSpec strict validation
- [ ] 9.8 Record launch metrics for landing conversion, login completion, index cost, paid conversion and gross margin without sensitive content
