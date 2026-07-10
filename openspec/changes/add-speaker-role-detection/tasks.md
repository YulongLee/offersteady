## 1. Protocol and Event Contracts

- [x] 1.1 Add source-kind and fixed candidate/interviewer display-role protocol types
- [x] 1.2 Define revisioned speaker transcript segment events with time range, finality and overlap
- [x] 1.3 Define question-candidate states, trigger reasons and stable source-segment references
- [x] 1.4 Define one idempotent QuestionConfirmed event shared by answer generation and billing
- [x] 1.5 Add protocol compatibility rules for clients without role-aware transcript support
- [x] 1.6 Add serialization and compatibility tests for every new event type

## 2. Audio Activity and Echo Suppression

- [x] 2.1 Define replaceable voice-activity and cross-channel echo-detection interfaces
- [x] 2.2 Preserve microphone, system and mixed source identities through the audio pipeline
- [x] 2.3 Implement time-aligned duplicate audio and transcript detection across channels
- [ ] 2.4 Prefer the microphone candidate segment when candidate speech echoes into system audio
- [x] 2.5 Mark unresolved simultaneous speech as overlap rather than forcing a clean transcript
- [ ] 2.6 Add synthetic tests for silence, noise, echo, delayed echo, duplicate frames and overlap

## 3. Source Routing and Anonymous Speaker Metadata

- [x] 3.1 Define a replaceable streaming diarization adapter and runtime capability result
- [ ] 3.2 Implement optional session-scoped anonymous speaker IDs for system-audio deduplication without exposing extra roles
- [x] 3.3 Map microphone/headset sources to candidate and system-audio sources to interviewer
- [x] 3.4 Present one or multiple remote speaker IDs through the single interviewer display role
- [x] 3.5 Implement conflict detection that suppresses auto-triggering and publishes source degradation without an unknown display role
- [ ] 3.6 Disable mixed-input automatic role routing and retain manual-input recovery
- [ ] 3.7 Delete temporary speaker features and audio buffers when the session ends
- [ ] 3.8 Add source-routing tests for dual channel, mixed channel degradation, shared device and multiple interviewers

## 4. Utterance and Question Detection

- [x] 4.1 Build revision-aware utterance assembly from interim and final transcript segments
- [x] 4.2 Implement configurable endpoint detection using silence, syntax and turn-change signals
- [x] 4.3 Define a replaceable question-intent detector for interrogative, imperative and short follow-up forms
- [x] 4.4 Combine multi-part interviewer setup and final question into one question candidate
- [x] 4.5 Reject acknowledgements, greetings, candidate answers and incomplete interviewer setup
- [x] 4.6 Mark low-confidence, overlapping and ambiguous candidates as needs-confirmation
- [ ] 4.7 Add multilingual fixtures for Chinese, English, mixed language, accents and technical terms
- [ ] 4.8 Add question-detection evaluations for recall, candidate false triggers, duplicates and latency

## 5. Trigger Gate and Idempotency

- [x] 5.1 Implement configurable source, transcript, boundary and question gates
- [x] 5.2 Publish auto-confirmed only when every trigger requirement passes
- [x] 5.3 Keep uncertain candidates unbilled and out of answer generation until user confirmation
- [x] 5.4 Generate stable candidate IDs from session and source transcript segment identities
- [x] 5.5 Merge interim and final revisions without creating duplicate questions
- [x] 5.6 Update confirmed question text without a second answer unless regeneration is explicit
- [x] 5.7 Bind exactly one answer task and one billing usage ID to QuestionConfirmed
- [ ] 5.8 Add concurrency tests for repeated transcript updates, reconnect replay and duplicate events

## 6. Two-Role Web Experience

- [ ] 6.1 Build live transcript rows for only “我” and “面试官”
- [x] 6.2 Distinguish interim, final, overlap and low-confidence transcript states without color alone
- [ ] 6.3 Show auto-confirmed, needs-confirmation and rejected question states
- [ ] 6.4 Add one-action confirmation, rejection and editable manual submission for uncertain questions
- [ ] 6.5 Add source-degradation recovery without role-correction controls
- [x] 6.6 Show mixed-input or source-unavailable degradation with manual-input recovery
- [ ] 6.7 Add desktop, tablet, mobile, keyboard and screen-reader tests for two-role and degradation controls

## 7. Privacy, Observability and Provider Boundaries

- [x] 7.1 Keep diarization, transcription and question-intent providers behind replaceable server adapters
- [ ] 7.2 Send each provider only the minimum audio or text needed for its stage
- [ ] 7.3 Prevent raw audio, speaker embeddings and full transcripts from entering ordinary logs
- [ ] 7.4 Record only redacted trigger decisions, confidence buckets, latency and error codes for monitoring
- [ ] 7.5 Add session-end cleanup verification for audio buffers and temporary speaker features
- [ ] 7.6 Add security tests for cross-session speaker IDs, unauthorized transcript access and provider-key exposure

## 8. Shadow Evaluation and Rollout

- [ ] 8.1 Create authorized or synthetic evaluation sets for dual channel, mixed audio, noise, echo, overlap and multiple interviewers
- [ ] 8.2 Define release thresholds prioritizing candidate false-trigger and duplicate-trigger rates
- [ ] 8.3 Run source routing and question detection in shadow mode without creating answers or charges
- [ ] 8.4 Compare automatic candidates against labelled source routes and question boundaries
- [ ] 8.5 Enable needs-confirmation mode only after shadow metrics pass its threshold
- [ ] 8.6 Enable auto-confirmed only for capability and language combinations that pass stricter thresholds
- [ ] 8.7 Run end-to-end tests from desktop dual-channel capture through one idempotent answer and charge
- [ ] 8.8 Document unsupported languages, device modes, failure behavior and manual fallback
