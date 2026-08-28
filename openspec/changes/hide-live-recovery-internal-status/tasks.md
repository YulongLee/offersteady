## 1. Correct Live Capture State

- [x] 1.1 Add an adapter regression proving healthy reported capture is not converted to reconnecting by preparing runtime readiness.
- [x] 1.2 Remove the runtime-preparing override while preserving explicit degraded and desktop-reported states.

## 2. Keep Recovery Internal

- [x] 2.1 Add application-state regressions proving reconnecting has no global alert while permission and error alerts remain visible.
- [x] 2.2 Remove reconnecting from the global live alert without changing the approved layout or automatic recovery behavior.

## 3. Verification

- [x] 3.1 Run focused Web regression tests and the Web type check/build.
- [x] 3.2 Run strict OpenSpec validation and review the final diff for scope and privacy compliance.
