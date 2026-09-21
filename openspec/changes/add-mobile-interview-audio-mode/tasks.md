## 1. Session Contract and Persistence

- [x] 1.1 Add the `computer` / `mobile` interview audio mode to Backend session domain models, API schemas, and Web domain mappings with a `computer` default
- [x] 1.2 Add an additive PostgreSQL migration and repository read/write support for the persisted audio mode
- [x] 1.3 Add a preparation-only API update operation and regression tests for defaults, persistence, and post-start locking

## 2. Web Entry and Preparation Experience

- [x] 2.1 Add a default-computer interview mode selector to realtime interview creation and send the selected mode when creating the draft
- [x] 2.2 Show mode-specific preparation copy, phone speaker placement guidance, and mode-aware readiness requirements
- [x] 2.3 Render mobile microphone transcripts with the localized “现场声音” semantic label while preserving computer-mode labels
- [x] 2.4 Add Web tests for selection persistence, preparation guidance, labels, and unchanged computer behavior

## 3. Desktop Audio Topology

- [x] 3.1 Read the persisted interview audio mode from companion pairing status and retain it across reconnects
- [x] 3.2 Start only the Mac microphone source in mobile mode and keep the existing dual-channel publisher in computer mode
- [x] 3.3 Make local audio checks and user-facing source errors mode-aware, with Desktop regression tests

## 4. Backend Realtime Routing

- [x] 4.1 Include the interview audio mode in pairing status and cache it safely for the realtime hot path
- [x] 4.2 Ignore unexpected system-audio frames in mobile mode without changing computer-mode source routing
- [x] 4.3 Allow eligible final mobile microphone transcripts into question confirmation, quick-answer, and opt-in automatic-answer flows
- [x] 4.4 Clear mode-specific cached state on all terminal cleanup paths and add realtime regression tests

## 5. AI Evaluation and Verification

- [x] 5.1 Add synthetic mobile mixed-audio transcript evaluation cases for complete questions, partial speech, candidate self-talk, and duplicates
- [x] 5.2 Run targeted Backend, Web, Desktop, and OpenSpec validation locally and record any unrelated pre-existing failures
- [x] 5.3 Confirm no deployment, server restart, release upload, or production configuration change occurred in this development pass

## 6. Domestic Production Release

- [x] 6.1 Publish Companion `1.3.1` artifacts and update the domestic release manifest
- [x] 6.2 Re-run release regressions and deploy the additive migration, Backend, and Web only after confirming no live interview is active
- [x] 6.3 Verify domestic health, release metadata, desktop downloads, and mobile/computer session contracts; record the rollback point

## 7. Mobile Publisher Hotfix

- [x] 7.1 Create a microphone-scoped transport publisher for mobile mode while preserving the computer mixed transport, with a Desktop regression test
- [x] 7.2 Run Desktop tests, type checking, build, and strict OpenSpec validation
- [x] 7.3 Publish Companion `1.3.2`, update the domestic release manifest, and deploy only after confirming no live interview is active
- [x] 7.4 Verify domestic release metadata, installer downloads, health, and mobile microphone publisher acceptance
