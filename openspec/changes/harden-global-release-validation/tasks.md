## 1. Release safety

- [x] 1.1 Add Global manifest validation and reject missing/stale/wrong-mode manifests before legacy deployment mutations; add synthetic regression tests.
- [x] 1.2 Add a read-only Docker image retention planner with reference protection and fail-closed inventory tests.

## 2. Regression verification

- [x] 2.1 Repair the three stale Global web assertions against current deployed behavior, record the historical homepage Spec discrepancy, and run the complete frontend suite and build.
- [x] 2.2 Run the isolated PostgreSQL material regression if local prerequisites are available; record exact results and outstanding real-device/concurrency acceptance.

## 3. Handoff

- [x] 3.1 Document usage, review requirements and limits; validate the OpenSpec change and each scenario without changing production.
