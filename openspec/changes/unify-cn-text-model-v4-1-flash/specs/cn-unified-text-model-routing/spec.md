## ADDED Requirements

### Requirement: CN text consumers use the approved replacement model

The CN backend and material worker SHALL explicitly configure `deepseek-v4.1-flash` as their shared text model while retaining independently configured quick and detailed models.

#### Scenario: Resume or JD is summarized
- **WHEN** the CN material worker summarizes a synthetic resume or JD after migration
- **THEN** its provider request uses `deepseek-v4.1-flash` with explicit non-thinking mode
- **AND** its existing summary parsing and output schema remain valid

#### Scenario: Mock question or report is generated
- **WHEN** CN generates a mock interview question or report after migration
- **THEN** its provider request uses `deepseek-v4.1-flash`
- **AND** the existing structured output, question limit and report safety checks remain valid

### Requirement: Migration preserves unrelated services and behavior

The migration MUST preserve quick/detail stage routing, prompts, billing, authentication, database content, desktop protocols, and all non-text-model configuration. Global production SHALL remain unchanged.

#### Scenario: Existing interview capabilities are inspected
- **WHEN** the CN migration completes
- **THEN** quick and detailed answers continue to use their existing `deepseek-v4.1-flash` overrides
- **AND** TTS, ASR, vision, embedding and rerank settings equal their pre-migration values

### Requirement: CN cutover is idle gated and verified

The migration MUST derive candidate images from the currently running images with only the approved explicit non-thinking summary parameter patch, and preserve their environment except the approved shared-model key. It SHALL be blocked by active ordinary/mock interviews, recent readiness/audio/page activity, pending answer work or pending material work. It MUST verify service health and effective settings before reporting success.

#### Scenario: User work is active
- **WHEN** pre-cutover checks detect protected work
- **THEN** application containers remain unchanged and deployment is deferred

#### Scenario: Idle cutover succeeds
- **WHEN** all gates are zero and synthetic adapter checks pass
- **THEN** only CN backend and material-worker configuration is switched
- **AND** both services load the replacement shared model with verified minimal overlay images and healthy service status

#### Scenario: Post-cutover validation fails
- **WHEN** a service fails startup or effective configuration validation
- **THEN** the previous configuration and identical images are restored without deleting data volumes

### Requirement: Provider verification is privacy safe

Verification MUST use synthetic inputs and MUST NOT log provider credentials or real user documents, audio or conversations.

#### Scenario: Provider probes run
- **WHEN** real provider compatibility checks are performed
- **THEN** outputs contain only synthetic fixture results, model identifiers and timing/check outcomes
- **AND** no real user session, quota or billing record is created
