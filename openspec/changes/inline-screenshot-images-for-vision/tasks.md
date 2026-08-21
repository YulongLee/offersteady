## 1. Configuration and delivery metadata

- [x] 1.1 Add a validated `inline` / `oss` screenshot vision delivery setting with `inline` as the default
- [x] 1.2 Extend screenshot timing telemetry with a non-sensitive delivery-mode field

## 2. Ephemeral inline screenshot pipeline

- [x] 2.1 Skip object-storage writes and signed URL generation in inline mode while preserving the existing OSS compatibility path
- [x] 2.2 Release transient screenshot bytes and upload bookkeeping after completed, failed and cancelled terminal states
- [x] 2.3 Keep screenshot prompt, answer ordering, billing and session-event behavior unchanged

## 3. Regression and verification

- [x] 3.1 Add regression tests proving inline mode never writes OSS and sends a Data URL to the vision gateway
- [x] 3.2 Add regression tests for terminal cleanup, telemetry privacy and OSS rollback mode
- [x] 3.3 Run screenshot-focused tests, backend test suite, type checks or compile checks, and strict OpenSpec validation
- [x] 3.4 Deploy only the affected backend service and verify production health plus screenshot model compatibility
