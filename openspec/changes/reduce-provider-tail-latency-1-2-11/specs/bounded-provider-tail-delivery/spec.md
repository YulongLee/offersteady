## ADDED Requirements

### Requirement: Clear speech endings use bounded adaptive release
The companion SHALL derive source-specific end-of-speech release from ambient context, turn envelope, and recent voice-like activity. It MUST end clear silence sooner than the conservative ceiling while preserving quiet trailing speech and ordinary short pauses.

#### Scenario: Strong speech falls clearly to ambient
- **WHEN** confirmed speech falls to a stable noise-relative level without recent voice-like variation
- **THEN** the companion emits one terminal within 700 milliseconds at P95 and retains all PCM through the selected tail

#### Scenario: Quiet trailing speech continues
- **WHEN** a quiet final word retains voice-like temporal activity above the calibrated source context
- **THEN** the companion keeps the current segment active and does not clip the word at the short release floor

#### Scenario: Speech resumes during an ordinary pause
- **WHEN** voice-like activity resumes before the adaptive release deadline
- **THEN** the companion continues the same segment without duplicate or missing PCM

### Requirement: Terminal commit is ordered and prioritized
The realtime path SHALL preserve every earlier same-source PCM byte before provider commit while preventing a terminal from waiting behind replaceable partial work or cold-path business processing. Terminal admission and commit scheduling MUST remain source-isolated.

#### Scenario: Terminal follows queued partial audio
- **WHEN** a terminal arrives while earlier partial PCM for the same segment remains queued
- **THEN** the backend processes the complete ordered PCM prefix before sending exactly one provider commit

#### Scenario: Source queue is saturated
- **WHEN** a terminal reaches a full source queue containing replaceable partial work
- **THEN** the terminal displaces or coalesces replaceable work without losing its PCM and is admitted within the configured terminal budget

#### Scenario: Another source is slow
- **WHEN** one source waits on a slow provider final
- **THEN** the other source can admit and commit its terminal without waiting for that final

### Requirement: Trailing provider revisions remain visible after commit
The Backend SHALL publish every unseen non-empty provider partial received after terminal admission and before provider completion. The Web SHALL immediately apply monotonic post-commit text growth without presenting the segment as actively transcribing, while provider final remains authoritative.

#### Scenario: Provider appends trailing words after commit
- **WHEN** a newer provider partial extends the visible hypothesis after terminal admission
- **THEN** the complete extended text becomes visible before provider final without restoring the active caret

#### Scenario: Provider retracts a post-commit hypothesis
- **WHEN** a non-final post-commit revision is shorter than the currently visible hypothesis
- **THEN** the Web preserves the longer visible draft until an equal-or-longer revision or authoritative final arrives

#### Scenario: Provider final corrects the draft
- **WHEN** the provider final differs from the frozen or extended draft
- **THEN** the Web accepts the final text as authoritative and rejects any later partial

### Requirement: Provider flush experiments are reversible
Any synthetic-silence suffix SHALL be disabled by default and controlled independently from endpointing and provider-final timeout. It MUST NOT be enabled for production unless measured real-provider acceptance improves tail latency without completeness or segmentation regression.

#### Scenario: Default production-compatible behavior
- **WHEN** no explicit flush experiment flag is enabled
- **THEN** the gateway sends the existing ordered audio followed directly by manual commit

#### Scenario: Isolated experiment is enabled
- **WHEN** a bounded synthetic-silence experiment is explicitly enabled
- **THEN** the gateway appends only the configured bounded zero-PCM duration before manual commit and reports content-free timing evidence

### Requirement: Tail latency evidence is privacy safe and commercially gated
The system SHALL measure speech-end, terminal admission, commit, last partial, provider final, event delivery, and browser presentation using timestamps, revisions, source metadata, and text lengths only. Diagnostics MUST NOT retain raw audio, transcript content, credentials, or personal data.

#### Scenario: Tail revision completes normally
- **WHEN** a provider partial or final is rendered after local speech end
- **THEN** the diagnostic path exposes stage durations and final-added-character count without transcript text

#### Scenario: Release candidate is verified
- **WHEN** 1.2.11 automated verification completes
- **THEN** tests demonstrate no terminal PCM loss, no partial-after-final regression, no UI/permission/identity change, and strict OpenSpec validation passes before local physical acceptance

### Requirement: Companion 1.2.11 preserves product compatibility
The companion SHALL identify as version 1.2.11 and preserve the approved layout, transparent icon family, application identity, permissions, production endpoint defaults, protocol compatibility, and privacy behavior on macOS Apple Silicon, macOS Intel, and Windows x64.

#### Scenario: Local Apple Silicon acceptance starts
- **WHEN** automated verification and the Apple Silicon production build pass
- **THEN** a local 1.2.11 companion is opened against the unchanged online service for user testing without deploying or reconfiguring production

#### Scenario: Other platform packages are prepared
- **WHEN** Intel macOS and Windows packages are built from the same tested revision
- **THEN** their metadata and deterministic behavior match 1.2.11 without claiming unperformed physical audio acceptance
