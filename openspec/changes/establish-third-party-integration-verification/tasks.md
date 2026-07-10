## 1. Verification capability design

- [x] 1.1 Confirm the verification scope, provider matrix, and non-goals in proposal and spec artifacts
- [x] 1.2 Define the Integration Report schema, step result schema, and sanitized logging contract
- [x] 1.3 Define the execution modes for full-suite runs and targeted reruns

## 2. Verification execution foundation

- [x] 2.1 Add a backend verification runner module that orchestrates provider-specific checks without changing prototype behavior
- [x] 2.2 Add shared verification models for suite status, step status, timing, metrics, and sanitized errors
- [x] 2.3 Add repeatable command or test entrypoints for full runs and selected provider runs

## 3. Provider verification adapters

- [x] 3.1 Implement OSS upload, object existence, and download verification
- [x] 3.2 Implement MinerU document parsing verification with synthetic document fixtures
- [x] 3.3 Implement Qwen chat, vision, embedding, rerank, and realtime ASR verification against real providers
- [x] 3.4 Implement PostgreSQL connectivity and pgvector extension / vector query verification

## 4. Reports, logs, and documentation

- [x] 4.1 Generate machine-readable and human-readable Integration Report outputs for every verification run
- [x] 4.2 Add structured verification logs with secret redaction and fixture-safe summaries
- [x] 4.3 Document required environment variables, fixtures, execution commands, and troubleshooting guidance

## 5. Validation

- [x] 5.1 Verify the change with `openspec validate establish-third-party-integration-verification --strict`
- [x] 5.2 Review the new spec scenarios to ensure all requested third-party integrations are covered
