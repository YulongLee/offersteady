## 1. Backend state and retry reliability

- [x] 1.1 Trace the current parser, processing-task and durable-job transitions for PDF uploads and document the exact state mismatch regression.
- [x] 1.2 Make retryable parser failures schedule durable retries without leaving a permanently queued task after the job retry limit is exhausted.
- [x] 1.3 Make retry exhaustion and non-retryable failures update task, durable job and document records to consistent terminal failure states.
- [x] 1.4 Preserve bounded, idempotent retries for `parser_invalid_result`, `object_load_failed` and provider transient failures while keeping unsupported/empty/deleted inputs non-retryable.
- [x] 1.5 Validate normalized parser output before marking a document ready and keep sensitive content out of logs.

## 2. Web processing status

- [x] 2.1 Extend upload status polling to a bounded 90-second window with terminal-state cancellation and page-unload cancellation.
- [x] 2.2 Show distinct processing, completed, failed and still-processing-after-timeout messages with a retry action where applicable.
- [x] 2.3 Keep existing upload API contracts and ensure a slow successful PDF is replaced in local state by the backend terminal state.

## 3. Regression tests

- [x] 3.1 Add backend regression tests for parser invalid-result retry, retry exhaustion, object-load failure and document deletion during processing.
- [x] 3.2 Add backend regression tests asserting task/job/document terminal-state consistency.
- [x] 3.3 Add Web regression tests for a PDF completing after the previous polling window and for polling stopping on failed/ready states.
- [x] 3.4 Run targeted backend and Web tests, type checks, build checks and strict OpenSpec validation; record only commands actually executed.

## 4. Production rollout

- [x] 4.1 Build the production artifact from the tested source and verify the image/config diff does not include unrelated changes.
- [x] 4.2 Read-only check the CN production service for active interviews and confirm there are zero before rollout.
- [x] 4.3 Deploy with the existing restart/switch procedure only after the no-active-interview gate passes.
- [ ] 4.4 Run an authenticated synthetic PDF upload and processing-status smoke test in production; health, route, worker and rollback checks are complete.
