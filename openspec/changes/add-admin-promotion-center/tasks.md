## 1. Product Decisions and Metric Contract

- [x] 1.1 Confirm the 30-day attribution window, 90-day visitor-cookie lifetime, 180-day raw-touchpoint retention, and `Asia/Shanghai` reporting timezone.
- [x] 1.2 Confirm that the main “使用” funnel stage means the first successfully started live interview and document desktop binding as a secondary diagnostic metric.
- [x] 1.3 Define and version the formulas and denominators for qualified UV, registration rate, activation rate, payment rate, CAC, ROAS, ROI, attributed paid revenue, direct, organic, and unattributed.
- [x] 1.4 Review the first-party analytics identifier, consent, retention, opt-out, and account-deletion behavior against the production privacy policy before enabling collection.

## 2. Persistence and Migration

- [x] 2.1 Add additive PostgreSQL migrations for promotion channels, campaigns, links, append-only costs, touchpoints, identity bindings, conversion events, attribution facts, metric snapshots, and analytics runs.
- [x] 2.2 Add uniqueness constraints for channel code, link slug, touchpoint event ID, identity claim, cost correction reference, and conversion source/model attribution.
- [x] 2.3 Add bounded query indexes for slug lookup, event time, visitor binding, user binding, paid-order attribution, campaign/channel/link dimensions, and daily snapshots.
- [x] 2.4 Add system buckets for direct, organic, and unattributed data without assigning historical records to a fabricated promotion source.
- [x] 2.5 Add repository tests for migration compatibility, idempotent upserts, immutable used-link attribution, cost reversal, concurrent identity claims, and duplicate paid-order aggregation.

## 3. Promotion Domain and Administrative APIs

- [x] 3.1 Implement promotion channel create/list/update/activate/deactivate operations with stable identifiers and management audit events.
- [x] 3.2 Implement campaign create/list/detail/update/status operations with objective, period, budget, notes, and cross-channel link aggregation.
- [x] 3.3 Implement promotion link create/list/detail/clone/activate/deactivate operations with random slugs and allowlisted internal destinations.
- [x] 3.4 Enforce channel/campaign immutability after a link receives its first qualified touchpoint and return a clone-based correction response.
- [x] 3.5 Implement append-only cost entry and explicit cost reversal APIs with reason, actor, date, scope, and currency validation.
- [x] 3.6 Add independent `promotion.read`, `promotion.manage`, and `promotion.cost.manage` permissions, recent-MFA rules where applicable, rate limits, pagination, and query timeouts.

## 4. Public Redirect and Visit Qualification

- [x] 4.1 Implement `GET /r/{slug}` with constant-shape safe errors, active-period validation, random first-party visitor/click cookies, and allowlisted internal redirects.
- [x] 4.2 Add a bounded Redis Stream producer for redirect-hit events with idempotency and safe counters; redirect success must not depend on queue availability.
- [x] 4.3 Implement an idempotent landing qualification endpoint using cookie-bound click context, page visibility, and minimum qualification rules.
- [x] 4.4 Implement known-bot/platform-preview classification, administrator preview exclusion, internal-test exclusion, and aggregate exclusion reasons without retaining raw IP or full UA.
- [x] 4.5 Add public redirect security tests for unknown, disabled, expired, malformed, enumerated, external-target, CRLF, and open-redirect attempts.
- [x] 4.6 Add latency and failure-injection tests proving redirect p95 and product access remain bounded when Redis, PostgreSQL, or the analytics worker is unavailable.

## 5. Identity Claim and Conversion Facts

- [x] 5.1 Implement an idempotent authenticated attribution-claim endpoint that reads first-party promotion cookies and never blocks successful login or registration.
- [x] 5.2 Add retryable pending-claim behavior and deterministic conflict handling for multiple browsers, multiple visitors, cleared cookies, and existing users.
- [x] 5.3 Record actual desktop package response-start events separately from download-button clicks and deduplicate them by visitor/user and artifact.
- [x] 5.4 Derive registration, first live interview, order, payment, payer, and revenue facts from `auth_users`, `interview_sessions`, and `billing_checkout_orders` rather than client declarations.
- [x] 5.5 Implement account-deletion cleanup that removes or irreversibly detaches promotion identity bindings and user-linked conversion facts while retaining non-identifying aggregates.

## 6. Attribution and Aggregation

- [x] 6.1 Implement versioned first-touch and last-non-direct-touch acquisition attribution over eligible qualified touchpoints within the confirmed window.
- [x] 6.2 Lock acquisition attribution at first registration, retain later assisting touches separately, and preserve explicit direct/organic/unattributed outcomes.
- [x] 6.3 Materialize conversion attribution with an exactly-once uniqueness boundary per authoritative source record and model version.
- [x] 6.4 Implement Cohort funnel aggregation with visitor/user deduplication, stage conversion, cumulative conversion, drop-off, maturity, and observation-window state.
- [x] 6.5 Implement daily promotion snapshots by attribution model, channel, campaign, and link plus bounded near-real-time current-day summaries.
- [x] 6.6 Implement append-only cost aggregation and coverage-aware CAC, ROAS, and ROI calculations that remain unavailable when costs are missing.
- [x] 6.7 Add an independent scheduled promotion analytics job with advisory locking, idempotent retries, gap repair, safe retention cleanup, health status, and no dependency on Web/Backend request success.
- [x] 6.8 Add a reconciliation job that compares attributed registration/order/payment totals with authoritative global totals and reports unexplained mismatches without modifying business records.

## 7. Promotion Reporting APIs

- [x] 7.1 Implement promotion overview APIs for today, yesterday, 7d, 30d, 90d, and bounded custom ranges with attribution-model and coverage metadata.
- [x] 7.2 Implement paginated link performance APIs with qualified hits, UV, registrations, activation, paid orders, revenue, cost, CAC, and ROAS.
- [x] 7.3 Implement campaign detail APIs with period, budget, actual cost, channel composition, trends, funnel, revenue, and ROI/ROAS coverage.
- [x] 7.4 Implement channel comparison APIs using identical filters, denominators, model version, bot rules, and timezone.
- [x] 7.5 Implement Cohort funnel APIs returning counts, stage/cumulative rates, drop-off, maturity, direct/organic/unattributed buckets, and freshness.
- [x] 7.6 Add reconciliation tests proving mutually exclusive link/channel/campaign rows sum to overview totals for the same model and range.
- [x] 7.7 Add query-plan and load tests proving reporting queries respect existing admin timeout/concurrency budgets and do not degrade user APIs.

## 8. Administrative User Interface

- [x] 8.1 Add a permission-aware “推广中心” navigation group without changing existing operations, payment, user, or server-monitoring pages.
- [x] 8.2 Build the promotion overview with KPI cards, trend chart, compact funnel, top channels/campaigns/links, attribution selector, date selector, coverage, and freshness states.
- [x] 8.3 Build promotion link management with create, copy, filter, detail, clone, activate, deactivate, safe destination validation, and no-count preview.
- [x] 8.4 Build campaign management with status, period, objective, budget, actual cost, channel mix, link list, conversion metrics, and coverage-aware ROI.
- [x] 8.5 Build channel analysis with sortable comparable metrics and explicit direct/organic/unattributed rows.
- [x] 8.6 Build the conversion funnel with counts, stage and cumulative rates, drop-off, observing/mature state, metric help, and empty/partial/delayed states.
- [x] 8.7 Build cost-entry and reversal interactions restricted by permission and requiring an explicit reason.
- [x] 8.8 Add responsive, keyboard, screen-reader, loading, error, retry, stale-data, and no-data tests while reusing the existing admin visual system.

## 9. Privacy, Security, and Operational Isolation

- [x] 9.1 Update product privacy documentation and public privacy text to accurately describe first-party promotion attribution, consent, retention, opt-out, and deletion behavior.
- [x] 9.2 Add schema and logging guards proving phone numbers, credentials, access tokens, raw IP, full UA/referrer, materials, transcripts, screenshots, and answers cannot enter promotion events or normal logs.
- [x] 9.3 Add abuse controls for slug scanning, qualification spam, replayed claims, forged conversion requests, bot bursts, and oversized metadata.
- [x] 9.4 Add analytics queue depth, dropped-event count, worker lag, snapshot freshness, attribution coverage, unmatched facts, and reconciliation health to administrator observability.
- [x] 9.5 Verify promotion collection, attribution, and reporting failures cannot fail registration, download, interview, ASR, quick answer, screenshot answer, checkout, payment callback, or entitlement delivery.

## 10. Verification and Rollout

- [x] 10.1 Create a fully synthetic end-to-end fixture covering two channels, one cross-channel campaign, multiple links, bots, direct traffic, repeated visits, registration, download, live use, unpaid order, paid order, costs, and account deletion.
- [x] 10.2 Verify first-touch and last-non-direct-touch outputs, exactly-once revenue, Cohort maturity, cost coverage, direct/unattributed handling, and all five management pages against the fixture.
- [x] 10.3 Run Backend/Admin/Web unit and integration suites, typechecks, production builds, migration checks, privacy checks, redirect benchmarks, analytics load tests, and strict OpenSpec validation.
- [ ] 10.4 Deploy additive migrations and disabled Backend/worker functionality first, then validate health and rollback without exposing the management navigation or public collection.
- [ ] 10.5 Gray-release redirect and visit qualification with internal no-count links, compare raw hits, qualified visits, bot exclusions, queue loss, and redirect latency.
- [ ] 10.6 Enable identity claims and read-only promotion reports, reconcile attributed totals against authoritative users/orders/payments, and observe at least one complete aggregation period.
- [ ] 10.7 Enable link/campaign/cost management only after data-quality acceptance; retain feature flags and a rollback path that hides the admin module and stops collection without deleting business or attribution facts.
