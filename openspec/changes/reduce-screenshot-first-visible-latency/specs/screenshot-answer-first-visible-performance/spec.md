## ADDED Requirements

### Requirement: Screenshot vision requests avoid hidden thinking latency
The system SHALL explicitly configure the screenshot vision model to return direct visible output without a hidden thinking phase by default, and MUST allow operators to roll back that behavior without changing other answer paths.

#### Scenario: Default screenshot request uses direct output
- **WHEN** the backend builds a streaming request for the configured screenshot vision model
- **THEN** the provider request explicitly disables thinking mode
- **AND** the model, prompt, image input and streaming behavior remain unchanged

#### Scenario: Operator rolls back the thinking setting
- **WHEN** an operator enables screenshot vision thinking through server configuration
- **THEN** only screenshot vision requests use the enabled value
- **AND** ASR and text-answer requests are unaffected

### Requirement: Screenshot first-visible latency is observable
The system SHALL record the provider first-visible-text latency and the browser first-render latency as distinct privacy-safe metrics, and MUST NOT store screenshot or answer content as part of those metrics.

#### Scenario: Provider returns its first visible text
- **WHEN** the screenshot vision stream yields its first non-empty visible content
- **THEN** the backend records the elapsed milliseconds as the AI usage first-token latency
- **AND** later chunks do not overwrite that first-token measurement

#### Scenario: Browser renders the first partial answer
- **WHEN** the browser first receives and renders non-empty answer text for a screenshot task
- **THEN** it acknowledges `screenshot-first-render` exactly once for that task
- **AND** the backend includes the duration in the screenshot click-to-render performance distribution

#### Scenario: Screenshot stream completes without content
- **WHEN** a screenshot task fails or completes without a non-empty visible response
- **THEN** no fabricated first-token or first-render latency is recorded

### Requirement: Existing screenshot and interview behavior remains compatible
The system MUST preserve the existing screenshot task lifecycle, partial answer delivery, final answer persistence, billing behavior and all non-screenshot interview chains.

#### Scenario: Multiple screenshot partials are delivered
- **WHEN** the provider emits multiple visible screenshot answer chunks
- **THEN** the browser continues to receive the existing accumulated partial and final answers
- **AND** the monitoring changes do not buffer, debounce or suppress those updates

#### Scenario: Other interview paths execute
- **WHEN** users use realtime ASR, quick answer or the desktop companion
- **THEN** their request parameters, user interface and runtime behavior are unchanged by this capability
