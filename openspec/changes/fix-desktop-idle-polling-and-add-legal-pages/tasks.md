## 1. Backend idle behavior

- [x] 1.1 Change the next remote screenshot endpoint to return a successful null result for unregistered, unbound, stale and non-live devices while preserving strict authorization on write endpoints
- [x] 1.2 Add backend regression tests for idle null responses, live pending requests, invalid screenshot writes and no activity/binding mutation

## 2. Desktop polling control

- [x] 2.1 Add a reusable non-overlapping polling/backoff policy with live, idle and failure intervals
- [x] 2.2 Make the main process the only remote screenshot poll owner and gate screenshot queries on a live pairing status
- [x] 2.3 Remove the renderer duplicate screenshot poll and convert binding status refresh to adaptive non-overlapping polling
- [x] 2.4 Add desktop regression tests for single ownership, live gating, idle interval, failure backoff and recovery

## 3. Public legal pages

- [x] 3.1 Add public `/terms` and `/privacy` routes with factual Chinese user agreement and privacy policy content
- [x] 3.2 Link both documents from login consent copy and the public footer with accessible link text
- [x] 3.3 Update Nginx route allowlisting and indexing headers so both routes return the SPA with `noindex, follow`
- [x] 3.4 Add Web route, content, link and production-routing regression tests

## 4. Documentation and verification

- [x] 4.1 Update privacy and desktop operation documentation with legal-page ownership and idle polling behavior
- [x] 4.2 Run targeted backend, desktop, Web and SEO tests plus workspace typecheck/build
- [x] 4.3 Validate the OpenSpec change strictly and record the deployment/production verification checklist
