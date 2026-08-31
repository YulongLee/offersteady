## 1. Screenshot Vision Request

- [x] 1.1 Add a server-side screenshot vision thinking-mode setting with a safe default and environment documentation
- [x] 1.2 Pass the explicit thinking-mode value only in screenshot vision provider requests
- [x] 1.3 Add a synthetic AI evaluation and regression test for direct non-thinking screenshot output

## 2. First-visible Monitoring

- [x] 2.1 Persist the first non-empty screenshot model text latency in the existing AI usage first-token field
- [x] 2.2 Record browser screenshot-first-render acknowledgements exactly once per task
- [x] 2.3 Add screenshot click-to-render to backend runtime performance distributions without logging content

## 3. Verification and Release

- [x] 3.1 Run strict OpenSpec validation and targeted backend/web regression tests
- [x] 3.2 Run the affected production builds and broader regression suite
- [x] 3.3 Commit the approved scope, deploy Backend/Web and the related metrics worker, and verify health, configuration and rollback readiness
