## 1. Context Selection Domain Model

- [x] 1.1 Split reusable library sources from per-interview prepared resources in the Web domain model
- [x] 1.2 Define source kind, processing state, version, updated-at and disabled/deleted metadata
- [x] 1.3 Define session context selection with resume, JD, knowledge source IDs, revision and confirmation state
- [x] 1.4 Define answer provenance with selection revision and concrete used source references
- [x] 1.5 Expand synthetic fixtures to include multiple resumes, JD documents and individual knowledge materials
- [x] 1.6 Add model tests for single-select resume/JD and multi-select knowledge constraints

## 2. Preparation Context Picker

- [x] 2.1 Replace the aggregate knowledge card with a “本场使用的资料” selection card
- [x] 2.2 Build single-select resume and JD sections with name, status, version and update time
- [x] 2.3 Build searchable multi-select knowledge materials with selected-count feedback
- [x] 2.4 Disable failed, processing, disabled and deleted materials with a clear management path
- [x] 2.5 Add explicit select-all and clear-all knowledge actions without selecting all by default
- [x] 2.6 Show recent-resume suggestions separately from confirmed selection
- [x] 2.7 Update personalized-readiness rules to require a confirmed valid resume and JD selection
- [x] 2.8 Persist and restore independent selections for two synthetic interviews
- [ ] 2.9 Add component tests for empty, suggested, selected, invalid and confirmed picker states

## 3. Live Interview Selection Changes

- [x] 3.1 Show the current selection summary and revision in the live workspace source panel
- [x] 3.2 Build a responsive live context-selection drawer using the same validation rules as preparation
- [x] 3.3 Keep unsaved drawer changes local and discard them on cancel
- [x] 3.4 Save live changes as a new revision and display that they apply from the next question
- [x] 3.5 Bind in-progress questions to the previous selection revision
- [ ] 3.6 Add tests for save, cancel, concurrent answer generation and responsive drawer behavior

## 4. Source Validity and Version Changes

- [x] 4.1 Compute valid, attention-required and blocked selection states
- [x] 4.2 Remove deleted or disabled sources from future retrieval eligibility without silently replacing them
- [ ] 4.3 Require confirmation before switching a selected source to a new parsed version
- [x] 4.4 Preserve minimal deleted-source labels for historical answer provenance without retaining content
- [ ] 4.5 Add tests for deletion, disablement, processing failure and version-update scenarios

## 5. Selection and Retrieval API

- [ ] 5.1 Define replaceable client APIs to load, confirm and revise a session context selection
- [x] 5.2 Define server request and response contracts for selection revision and answer provenance
- [x] 5.3 Implement authorization checks for user, session, source ownership and selection revision
- [x] 5.4 Pass only server-validated allowed source IDs to the replaceable retrieval adapter
- [x] 5.5 Reject client-supplied unselected IDs without logging source names or document content
- [x] 5.6 Add API security tests for cross-user, wrong-session, stale-revision and unselected-source requests

## 6. Answer Provenance Presentation

- [x] 6.1 Return actual used source IDs, versions, kinds and display names with each answer event
- [x] 6.2 Replace generic source-type pills with concrete source names in live and review pages
- [x] 6.3 Keep source evidence, model inference and generated advice visually and semantically separate
- [x] 6.4 Exclude selected-but-not-retrieved materials from answer provenance
- [ ] 6.5 Add synthetic retrieval evaluations for irrelevant, conflicting and excessive selected materials
- [ ] 6.6 Add component tests for zero, one, multiple and deleted actual sources

## 7. End-to-End Verification

- [x] 7.1 Verify separate context selections across two interview preparation flows
- [x] 7.2 Verify a live selection revision affects the next question but not the current or historical answer
- [x] 7.3 Verify source deletion immediately excludes future retrieval while preserving minimal history labels
- [ ] 7.4 Run desktop, tablet and mobile visual checks for the preparation picker and live drawer
- [ ] 7.5 Run keyboard, screen-reader naming, contrast and 44×44 touch-target checks
- [ ] 7.6 Verify all specification scenarios with synthetic or redacted source content
