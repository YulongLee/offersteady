## 1. Configuration and provider selection

- [x] 1.1 Add an explicit realtime ASR protocol setting and document the Qwen Audio task protocol values
- [x] 1.2 Select the new or legacy gateway in Backend dependency wiring with production-safe validation

## 2. Qwen Audio streaming adapter

- [x] 2.1 Implement source-scoped inference-task WebSocket connection and task warmup
- [x] 2.2 Stream bounded raw PCM binary frames and publish non-empty intermediate revisions
- [x] 2.3 Finish each application segment, return authoritative final text, and prestart the next reusable task
- [x] 2.4 Classify provider failures and close only the affected source connection
- [x] 2.5 Expose content-free connection/task/result diagnostics

## 3. Verification and switching

- [x] 3.1 Add unit regressions for lifecycle, binary audio, partial/final mapping, source isolation, timeout, and protocol selection
- [x] 3.2 Update integration verification for both supported ASR protocols without logging credentials or transcripts
- [x] 3.3 Run focused and full Backend tests, type/compile checks, strict OpenSpec validation, and diff checks
- [x] 3.4 Run a live synthetic-audio roundtrip through the implemented adapter
- [x] 3.5 Prepare the new public endpoint/model/protocol configuration with the legacy rollback tuple documented
