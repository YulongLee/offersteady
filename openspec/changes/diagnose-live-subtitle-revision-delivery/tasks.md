## 1. Baseline Audit

- [x] 1.1 Map the production Qwen Partial, Redis XADD/XREAD, SSE, Browser merge, React commit and visible-text paint path
- [x] 1.2 Record current SSE headers, Nginx buffering configuration and all batch/debounce/throttle/timer points without changing them

## 2. Backend Revision Trace

- [x] 2.1 Add bounded feature-gated revision trace fields and stable identifiers from Qwen receipt through event creation
- [x] 2.2 Record Redis XADD start/complete and XREAD receive timestamps for the same revision without changing repository behavior
- [x] 2.3 Record SSE generator yield and reliable ASGI chunk-write evidence, or explicitly mark chunk-write unavailable
- [x] 2.4 Extend content-free performance trace reporting with per-stage revision counts, gaps, loss accounting and visible-only distributions
- [x] 2.5 Add Backend regression tests for identifiers, stage timestamps, bounds, privacy and unchanged event ordering

## 3. Browser and React Trace

- [x] 3.1 Record Browser chunk receive, SSE parse and transcript-store update start/complete per revision
- [x] 3.2 Record React component render start, commit and next-frame paint confirmation for the actual visible transcript text
- [x] 3.3 Send content-free Browser acknowledgements asynchronously without blocking product state updates
- [x] 3.4 Add an explicitly enabled, isolated Debug Overlay for stage ages, counts, revision and visibility
- [x] 3.5 Add Web regression tests for revision identity, state projection metadata, privacy and overlay isolation

## 4. Verification and Real Test

- [x] 4.1 Run focused Backend/Web tests, full relevant suites, type checks and production builds
- [x] 4.2 Validate the OpenSpec change strictly and document exact diagnostic enable/disable procedure
- [ ] 4.3 After explicit deployment authorization, run a visible System-only real-chain test with Microphone off and at least 50 utterances
- [ ] 4.4 Export Qwen/SSE/Browser/Render revision counts, gap distributions, latency percentiles, Top slow samples and one content-redacted waterfall
- [ ] 4.5 Answer only the five requested diagnostic conclusions and do not implement a latency fix without separate approval
