## ADDED Requirements

### Requirement: Live readiness is authoritative and source-scoped
The system SHALL expose microphone and system-audio capture readiness independently and SHALL NOT derive `live-ready` from interview lifecycle or desktop transport presence alone.

#### Scenario: One capture source is unavailable
- **WHEN** the desktop transport is connected but system-audio capture failed to open
- **THEN** the runtime reports microphone and system-audio states independently and does not claim that both sources are ready

#### Scenario: A capture source is silent
- **WHEN** a source capture graph opened successfully but currently contains silence
- **THEN** the runtime reports the source as ready without requiring transcript frames

### Requirement: Active interviews reconstruct provider readiness
The backend SHALL idempotently prewarm enabled provider sources when an interview starts and when an authenticated publisher attaches to an already-live capturing interview.

#### Scenario: Backend restarts during an active interview
- **WHEN** the desktop publisher reattaches after process-local provider sessions were lost
- **THEN** the backend reconstructs both enabled source sessions without requiring the interview to be recreated

#### Scenario: First audio races reconstruction
- **WHEN** a first frame arrives while its source is being rewarmed
- **THEN** the frame shares the single-flight source creation and is neither duplicated nor discarded

### Requirement: Readiness has bounded user-visible timing
The local release SHALL measure readiness without transcript or audio content and target click-to-live-ready P95 at or below two seconds with a four-second bounded degraded transition.

#### Scenario: Provider readiness exceeds the deadline
- **WHEN** one provider source cannot become ready within the configured deadline
- **THEN** the existing live interface remains usable but reports the affected realtime source as preparing or degraded instead of silently claiming immediate readiness

### Requirement: Existing presentation is preserved
The 1.2.2 companion and Web change SHALL preserve the existing layout, icons, branding, and explicit interview controls.

#### Scenario: Readiness status changes
- **WHEN** a source transitions between preparing, ready, and degraded
- **THEN** only the existing status presentation updates and the surrounding layout does not change
