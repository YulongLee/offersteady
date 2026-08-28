## ADDED Requirements

### Requirement: Release companion version 1.2.4 consistently
The product SHALL identify the next desktop patch as version 1.2.4 and SHALL build synchronized macOS arm64, macOS x64, and Windows x64 artifacts without changing the existing bundle identifier, production origins, or realtime protocol.

#### Scenario: Inspect supported release artifacts
- **WHEN** the 1.2.4 release is prepared for publication
- **THEN** all three supported artifacts report version 1.2.4 and their manifest filenames, sizes, architectures, signing status, and SHA-256 values match the published files

### Requirement: Use transparent-corner companion icons
The companion MUST use text-free icon assets with a real alpha channel and transparent external corners for both operating-system packaging and the in-app brand mark. The core shield, microphone, and confirmation mark MUST remain recognizable at small sizes.

#### Scenario: Operating system renders the installed icon
- **WHEN** macOS or Windows renders the 1.2.4 application at launcher, Dock, taskbar, or installer sizes
- **THEN** the icon does not display an opaque white square canvas around the intended rounded icon

#### Scenario: Companion renders its brand mark
- **WHEN** the 1.2.4 companion window opens
- **THEN** the in-app brand mark uses the same transparent visual family and does not depend on CSS clipping to hide opaque corner pixels

#### Scenario: Release validation inspects icon semantics
- **WHEN** icon regression and package verification run
- **THEN** they verify alpha-capable source metadata, transparent corner pixels, and the generated macOS and Windows package resources rather than accepting an opaque asset solely because its hash is pinned

### Requirement: Open the Web workspace instead of a bound interview
The companion SHALL expose a website action that opens the configured OfferSteady Web workspace root and MUST NOT derive a session-specific live-interview route from the current active binding.

#### Scenario: Bound companion opens the website
- **WHEN** the companion has an active binding and the user selects the website action
- **THEN** the system opens the configured `/app` workspace and does not open `/app/interviews/{sessionId}/live`

#### Scenario: Unbound companion opens the website
- **WHEN** the companion has no active binding and the user selects the website action
- **THEN** the system opens the same configured `/app` workspace behavior used in the bound state

#### Scenario: Website navigation preserves interview state
- **WHEN** the website action is used while audio capture or an interview binding exists
- **THEN** the companion does not automatically create, enter, resume, switch, end, or disconnect an interview and does not alter capture or binding state

### Requirement: Preserve the accepted desktop product boundary
Version 1.2.4 MUST preserve the 1.2.3 companion layout, permission behavior, device identity, protocol compatibility, screenshot workflow, and separate homepage/guide actions except for the approved icon, website action, latency, endpointing, and health-recovery changes.

#### Scenario: Compare 1.2.4 with 1.2.3
- **WHEN** release regression checks compare changed desktop behavior
- **THEN** only the approved icon assets, icon validation, version/release metadata, website action label/target, and specified realtime orchestration/health behavior differ in the affected product surface

#### Scenario: Permission status is unavailable
- **WHEN** macOS reports system-audio permission as denied or unavailable
- **THEN** the accepted three-row companion layout and fixed row copy remain unchanged, and no conditional inline permission button expands the computer-output row

### Requirement: Start the bound live capture promptly
The system SHALL avoid serial user-facing waits for desktop binding polling and ASR prewarm when an already-online companion enters a live interview. Provider prewarm SHALL remain asynchronous and failure-tolerant.

#### Scenario: Web starts a bound interview
- **WHEN** the Web marks an interview live while its companion is online and waiting
- **THEN** the companion detects the live transition on a short bounded cadence and begins capture without waiting for the previous ten-second idle interval

#### Scenario: Provider prewarm is slow
- **WHEN** one or both ASR prewarm operations exceed the normal warm-up target
- **THEN** the start-session response completes without waiting for the full prewarm timeout and real audio can initialize the provider path

### Requirement: Bound visible speech completion
The desktop SHALL continue publishing incremental revisions during speech and SHALL bound long system-audio turns without waiting twelve seconds for every continuous/noisy source. The Backend MUST expose user-perceived completion latency from the last meaningful speech timestamp to publication.

#### Scenario: System audio has no clean silence boundary
- **WHEN** system audio remains above the continuation threshold after meaningful speech
- **THEN** the companion commits a bounded turn earlier than the 1.2.3 twelve-second maximum while preserving subsequent audio in a new revision-safe turn

#### Scenario: Speaker stops after one sentence
- **WHEN** the client detects the configured silence tail
- **THEN** it emits an authoritative terminal frame and reports last-meaningful-speech-to-publish latency without waiting for another sentence

### Requirement: Clear recovered transport failures
The companion MUST clear stale transport error and reconnect fields after a source resumes healthy capture and acknowledged delivery.

#### Scenario: Publisher reconnect succeeds
- **WHEN** a source previously reported `publisher-transport-missing` or `audio-gap` and later resumes accepted frames
- **THEN** subsequent device health reports no longer carry that stale error as the current source failure

### Requirement: Recover Web diagnostics from authoritative health
The Web SHALL refresh runtime readiness after health-affecting device events, SHALL remove a false global error after recovery, and MUST make the “重新诊断” action request authoritative state rather than only mutating local display state.

#### Scenario: Degraded source recovers
- **WHEN** the Web initially receives degraded runtime state and the source later becomes silent or receiving with healthy delivery
- **THEN** a later runtime update restores the capturing state and removes the global connection-error banner

#### Scenario: User selects re-diagnosis
- **WHEN** the user selects “重新诊断” on the live page
- **THEN** the Web fetches current session runtime/snapshot state and renders its result without changing the interview or capture state optimistically
