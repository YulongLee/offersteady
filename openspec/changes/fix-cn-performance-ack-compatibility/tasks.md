## 1. Baseline and reproduction

- [x] 1.1 Verify running-image and source hashes, preserve an independent source snapshot, and reproduce the actual route failure with synthetic requests.

## 2. Compatibility repair

- [x] 2.1 Restore three optional timestamp parameters and diagnostic mappings without unrelated source changes.
- [x] 2.2 Test all four telemetry stages, omitted/null/populated fields, ownership rejection and content rejection against the exact source snapshot and candidate image.

## 3. Safe rollout

- [x] 3.1 Preserve the old image and configuration, verify zero live interviews/audio, and replace only Chinese Backend.
- [x] 3.2 Verify deployed hashes, isolated route acceptance, health and fresh error logs; record limitations and run strict OpenSpec validation.
