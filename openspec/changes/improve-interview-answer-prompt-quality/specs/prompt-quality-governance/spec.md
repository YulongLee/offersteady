## ADDED Requirements

### Requirement: Production answer prompts are centralized and versioned
All production policy text that controls live interview or screenshot answer behavior SHALL be stored under `ai/prompts/` as versioned templates or reusable prompt components. Runtime services MAY assemble those components but MUST NOT maintain an independent hard-coded production answer policy.

#### Scenario: A live answer is generated
- **WHEN** Chat Service starts an answer task
- **THEN** the task records the effective prompt template ID and version used for both quick and detailed stages

#### Scenario: A screenshot answer is generated
- **WHEN** Screenshot Answer Service invokes the vision model
- **THEN** the task records the effective screenshot prompt template ID and version

### Requirement: Prompt releases pass synthetic quality evaluation
Every production prompt behavior change MUST update or add synthetic cases under `ai/evals/` and SHALL be evaluated against the current production baseline before rollout. Fabrication, source isolation, privacy and complete code-answer checks MUST NOT regress.

#### Scenario: Candidate prompt fails grounding
- **WHEN** a candidate prompt invents an unsupported project metric in any grounding eval
- **THEN** the prompt version is not eligible for production rollout

#### Scenario: Candidate prompt improves style
- **WHEN** a candidate prompt preserves all safety checks and improves directness, natural speech or follow-up consistency
- **THEN** the comparison report records the improvement and the version may proceed to staged rollout

### Requirement: Prompt quality telemetry preserves privacy
The system SHALL record privacy-safe prompt metadata sufficient to compare versions, including template ID, version, strategy mode, source counts, character or token buckets, latency, completion status and safe error code. It MUST NOT log raw prompts, material bodies, screenshots, full transcripts or full model answers.

#### Scenario: Production answer completes
- **WHEN** a live or screenshot answer completes in production
- **THEN** operators can compare latency and completion outcomes by prompt version without accessing the user's content

### Requirement: Prompt versions can be rolled back without code or data migration
The deployment configuration SHALL support selecting the previous known-good prompt version. Rollback MUST preserve existing sessions, answer history and material bindings.

#### Scenario: New prompt quality regresses
- **WHEN** staged monitoring or user testing identifies a material quality regression
- **THEN** operators can restore the previous prompt version without changing stored user data or the frontend contract
