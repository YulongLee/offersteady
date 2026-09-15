## 1. Discovery and configuration

- [x] 1.1 Confirm the Baidu product's credential protocol and production endpoint from its delivery documentation.
- [x] 1.2 Add server-only settings for endpoint, credentials, domain, keywords, timezone, timeout/retry, and manual-refresh policy.
- [ ] 1.3 Rotate the credentials shown in the screenshot before any production configuration.

## 2. Backend persistence and provider

- [x] 2.1 Add the ranking snapshot schema, unique daily key, indexes, and migration/bootstrap wiring.
- [x] 2.2 Implement a replaceable Baidu ranking client with form encoding, timeout, bounded retry, safe error mapping, and response validation.
- [x] 2.3 Implement the idempotent daily synchronization service and worker entry point.

## 3. Admin API and permissions

- [x] 3.1 Add `seo.read` permission mapping and protected latest/history summary endpoints.
- [x] 3.2 Add audited manual refresh endpoint with rate limiting and explicit reason.
- [x] 3.3 Add keyword list CRUD endpoints with validation and audit for manager actions.
- [x] 3.4 Ensure responses and audit details cannot contain provider credentials or raw sensitive payloads.

## 4. Admin UI

- [x] 4.1 Add a Search Rankings navigation item visible only with the read permission.
- [x] 4.2 Render keyword management controls for managers and up to 50 results per keyword.
- [x] 4.3 Render last sync status, observed date, rank/not-found/error state, previous delta, URL/title, and stale-data notice.
- [x] 4.4 Add the audited manual refresh action with clear quota/status feedback.

## 5. Verification and rollout

- [x] 5.1 Add unit tests for configuration secrecy, response parsing, rank semantics, idempotency, timeout/retry, and permissions.
- [x] 5.2 Add frontend/API regression tests for table rendering and no-provider-call-on-load behavior.
- [x] 5.3 Run lint, typecheck, backend tests, build, and `openspec validate add-baidu-ranking-monitoring --strict`.
- [ ] 5.4 Deploy with sync disabled, configure rotated credentials out-of-band, run one controlled sync, then enable the daily schedule.
