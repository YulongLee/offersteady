## 1. Baseline and implementation

- [x] 1.1 Verify running CN model routing, image/config baseline and protected-work gates without exposing secrets.
- [x] 1.2 Update configuration example/documentation, explicitly disable summary thinking, and add regression tests plus synthetic AI eval fixtures.

## 2. Verification

- [x] 2.1 Run focused local backend regressions and strict OpenSpec validation.
- [x] 2.2 Verify synthetic resume/JD summaries and mock question/report through current adapters with real v4.1 provider; record timing and structural/safety checks.

## 3. CN cutover

- [x] 3.1 Build minimal candidate overlays from actual CN runtime images and preserve all unrelated configuration.
- [x] 3.2 After idle gates pass, back up configuration and switch only CN backend/material worker with rollback on failed health checks.
- [x] 3.3 Verify effective models, non-text invariance and service health; document deployment and remaining TTS retirement risk.
