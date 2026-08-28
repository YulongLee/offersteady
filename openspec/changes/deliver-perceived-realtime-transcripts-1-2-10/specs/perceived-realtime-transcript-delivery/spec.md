## ADDED Requirements

### Requirement: Provider partials remain continuously visible while speech is ongoing
The realtime path SHALL publish every new non-empty provider transcript revision independently from audio append workers, question detection, persistence, and provider finalization. The Web SHALL display the complete newest monotonic partial immediately without synthetic reveal delay.

#### Scenario: Provider produces multiple revisions before speech ends
- **WHEN** a persistent source session receives successive unseen provider partial revisions for one segment
- **THEN** each revision is eligible for immediate SSE delivery and the Web displays the newest complete revision before terminal commit

#### Scenario: Provider temporarily retracts text
- **WHEN** a non-final provider revision is shorter than the newest visible partial
- **THEN** the Web preserves the longer visible hypothesis until an equal-or-longer revision or authoritative final reconciles it

### Requirement: System-output speech ends from voice-aware temporal evidence
The companion SHALL use source-specific adaptive noise context, sustained admission, hysteresis, and bounded temporal voice evidence to release system-output speech. Low residual program energy without recent voice-like variation MUST NOT refresh meaningful speech indefinitely, and maximum duration MUST remain a safety boundary rather than the normal endpoint.

#### Scenario: Speech ends over residual program energy
- **WHEN** system speech is followed by steady low residual output above the simple continuation floor but without recent voice-like temporal variation
- **THEN** the companion emits one silence terminal within 500 milliseconds at P95 instead of waiting for the maximum-turn boundary

#### Scenario: Speech continues across an ordinary short pause
- **WHEN** voice-like system output resumes within the configured short tail
- **THEN** the companion keeps one segment and does not discard or duplicate the resumed audio

#### Scenario: Quiet system speech begins
- **WHEN** sustained quiet speech varies measurably above the calibrated source baseline
- **THEN** the first partial audio frame retains the bounded pre-speech window and is published within 400 milliseconds at P95

### Requirement: Visible completion does not wait for provider finalization
After Backend terminal admission, the Web SHALL immediately stop presenting the segment as actively transcribing, freeze the latest visible partial, and continue authoritative final reconciliation in the background. The Web MUST NOT infer `incomplete` from client-side elapsed time; only an explicit Backend terminal state may present incomplete.

#### Scenario: Terminal is admitted before provider final
- **WHEN** the Backend emits `transcript-committing` for a visible partial
- **THEN** the Web stops the active caret immediately, preserves the text, and does not show incomplete while waiting for provider final

#### Scenario: Provider final arrives normally
- **WHEN** the Backend later publishes an authoritative final revision
- **THEN** the final text monotonically reconciles the frozen partial without re-entering transcribing

#### Scenario: Provider final is unavailable
- **WHEN** the Backend explicitly terminalizes the segment as `incomplete`
- **THEN** the Web preserves the latest text and presents incomplete exactly once

### Requirement: Companion 1.2.10 is reversible and product compatible
The 1.2.10 local acceptance build SHALL preserve the approved companion layout, transparent icon family, application identity, production endpoint configuration, signing settings, privacy defaults, and protocol compatibility.

#### Scenario: Local acceptance build is opened
- **WHEN** automated Desktop, Backend, Web, protocol, typecheck, build, and strict specification verification pass
- **THEN** an isolated local Backend/Web chain and Apple Silicon 1.2.10 companion are opened for physical user acceptance without changing production
