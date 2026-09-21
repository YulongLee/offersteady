## ADDED Requirements

### Requirement: Live answer stages use independently configurable models

The backend SHALL select server-only stage models for live quick and detailed answers. The quick model applies to quick generation, normalized-question output, language-repair retry, and quick-stage continuation. The detail model applies to detailed generation, language-repair retry, and detail-stage continuation. Other AI capabilities MUST retain their existing model selection.

#### Scenario: Dedicated quick model configured
- **WHEN** the server configures `OFFERSTEADY_CHAT_QUICK_MODEL=deepseek-v4.1-flash` and a user requests a quick answer
- **THEN** every provider request belonging to the quick stage uses `deepseek-v4.1-flash`
- **AND** the later detailed-answer stage uses `OFFERSTEADY_CHAT_DETAIL_MODEL` when configured

#### Scenario: Dedicated detail model configured
- **WHEN** the server configures `OFFERSTEADY_CHAT_DETAIL_MODEL=deepseek-v4.1-flash` and a user requests a detailed answer
- **THEN** every provider request belonging to the detail stage uses `deepseek-v4.1-flash`
- **AND** document summaries and generic non-live chat continue to use `OFFERSTEADY_CHAT_QWEN_MODEL`

#### Scenario: Dedicated stage model omitted
- **WHEN** either `OFFERSTEADY_CHAT_QUICK_MODEL` or `OFFERSTEADY_CHAT_DETAIL_MODEL` is empty or absent
- **THEN** that stage uses `OFFERSTEADY_CHAT_QWEN_MODEL` and preserves the existing behavior

### Requirement: Quick model routing remains observable and private

The backend MUST record the actual selected model and stage in privacy-safe provider telemetry and task metadata without logging the question, answer, transcript, resume, job description, or retrieved evidence.

#### Scenario: Quick and detail provider requests complete
- **WHEN** a two-stage live answer uses different quick and detail models
- **THEN** provider telemetry identifies the actual model for each request
- **AND** no user content is added to the telemetry

### Requirement: Candidate live-answer models pass synthetic release checks

Before production enablement, the candidate quick and detail models MUST pass synthetic compatibility and regression checks for Chat Completions, non-thinking streaming, normalized-question parsing, answer completeness, selected-language output, grounding safety, and quick/detail consistency.

#### Scenario: Local candidate verification
- **WHEN** the quick and detail provider probes run against `deepseek-v4.1-flash` with synthetic interview data
- **THEN** the quick probe returns a parseable normalized question and non-empty quick answer
- **AND** the detail probe returns a grounded detailed answer that preserves the quick-stage anchor
- **AND** neither probe exposes real user data
- **AND** focused backend and AI evaluation regressions pass
