## 1. Realtime shortcut acceptance

- [x] 1.1 Add and test the realtime event emitted only after a shortcut capture request is accepted
- [x] 1.2 Map the accepted event from the existing session SSE into a request-scoped screenshot update

## 2. Web feedback reconciliation

- [x] 2.1 Show the waiting screenshot dialog immediately from the realtime update
- [x] 2.2 Reconcile realtime acceptance, low-frequency progress, cancellation, and completion by request ID without duplicates
- [x] 2.3 Add regression tests covering immediate feedback and the unchanged recovery poll interval

## 3. Verification

- [x] 3.1 Run focused backend and web tests, typecheck/build checks, and strict OpenSpec validation
