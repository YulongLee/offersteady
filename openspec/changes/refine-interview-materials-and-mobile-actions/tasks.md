## 1. Spec Reconciliation and Shared Contracts

- [x] 1.1 Reconcile optional material behavior with `add-per-interview-context-selection` required-context scenarios
- [x] 1.2 Reconcile main-region live actions with `add-web-interview-application` and `add-speaker-role-detection`
- [x] 1.3 Define selection-integrity and context-level types without duplicating `SessionContextSelection`
- [x] 1.4 Add protocol tests for confirmed empty, partial and personalized selection serialization
- [x] 1.5 Add backward-compatibility handling for existing selections that have no explicit context-level field

## 2. Categorized Material Management

- [x] 2.1 Refactor the material page into Resume, Job Description and Knowledge Base sections
- [x] 2.2 Implement resume list, upload, processing-state, replace and delete prototype flows
- [x] 2.3 Implement JD list, paste/file add, processing-state, replace and delete prototype flows
- [x] 2.4 Preserve knowledge collections, document indexing, point disclosure and deletion behavior
- [x] 2.5 Map all three sections to the shared source ownership, status and version model
- [x] 2.6 Add clear empty states and contextual links from each section to interview preparation
- [x] 2.7 Expand synthetic fixtures with multiple resumes, multiple JDs and independent knowledge sources
- [x] 2.8 Add tests proving material creation does not automatically authorize an interview
- [x] 2.9 Add ownership, processing, replacement and deletion regression tests for each material type

## 3. Optional Per-Interview Selection

- [x] 3.1 Split selection integrity from derived context level in Web domain logic
- [x] 3.2 Add explicit “不使用” choices for resume and JD and retain “全部取消” for knowledge materials
- [x] 3.3 Add a one-action “本场不使用资料” path with a concise impact disclosure
- [x] 3.4 Allow confirmed empty and partial selections while rejecting unready or unauthorized selected sources
- [x] 3.5 Change interview start gating to require confirmed selection, input readiness and privacy confirmation rather than resume/JD presence
- [x] 3.6 Display none, partial and personalized context levels in the preparation checklist without treating empty context as an error
- [x] 3.7 Ensure recent-material suggestions remain unselected until explicit confirmation
- [x] 3.8 Persist empty selections with `confirmedAt` and an incremented revision
- [x] 3.9 Handle deletion or invalidation of a selected source without silently selecting a replacement
- [x] 3.10 Add preparation tests for empty, resume-only, JD-only, knowledge-only, partial and personalized starts
- [x] 3.11 Verify separate empty or partial selections remain isolated across two interview drafts

## 4. Retrieval Scope and Answer Provenance

- [x] 4.1 Update the trusted selection API to accept and persist a confirmed empty allowlist
- [x] 4.2 Ensure retrieval adapters receive only server-validated selected source IDs
- [x] 4.3 Skip personal-material retrieval for an empty allowlist without falling back to other user sources
- [x] 4.4 Return empty `usedSources` and a “未使用个人资料” presentation state for no-context answers
- [x] 4.5 Preserve exact source names and versions for partial-context answers
- [x] 4.6 Add authorization tests for injected, deleted, unready and unselected source IDs
- [x] 4.7 Add AI evaluation cases for no-context and partial-context answers that must not fabricate candidate experience
- [x] 4.8 Add regression tests proving an empty selection never reads the user's latest resume, JD or knowledge collection

## 5. Main-Region Live Action Composer

- [x] 5.1 Extract pending-question, manual-draft and screenshot-task state into one live-session action model
- [x] 5.2 Build `LiveActionComposer` in the current question and answer main region
- [x] 5.3 Move “不是问题” and “确认并回答” from the speaker side panel into the composer
- [x] 5.4 Move the canonical screenshot-answer entry from the materials side panel into the composer
- [x] 5.5 Move the canonical manual-question input from the materials side panel into the composer
- [x] 5.6 Keep speaker diagnostics in the secondary panel without retaining a side-panel-only confirmation path
- [x] 5.7 Preserve screenshot preview, upload, recognition, failure and retry states after the move
- [x] 5.8 Preserve point or membership disclosure before normal-answer and screenshot submission
- [x] 5.9 Keep command idempotency and prevent duplicate point settlement across repeated taps
- [x] 5.10 Add tests for pending-question confirmation, dismissal, manual submit and screenshot submit from the main region
- [x] 5.11 Add tests proving both side panels can be collapsed without losing primary actions

## 6. Mobile Reachability and Accessibility

- [x] 6.1 Implement the compact phone action bar using the same `LiveActionComposer` state and commands
- [x] 6.2 Define shared CSS height variables for mobile navigation, session controls, action bar and safe-area offsets
- [x] 6.3 Add sufficient main-content and drawer bottom spacing so fixed controls do not cover answers or actions
- [x] 6.4 Make every primary phone action at least 44×44 CSS pixels with text or accessible names
- [x] 6.5 Preserve manual drafts and screenshot tasks across viewport breakpoint changes and drawer toggles
- [x] 6.6 Handle the on-screen keyboard without permanently obscuring the input or submit action
- [x] 6.7 Add keyboard focus order, status announcements, disabled reasons and non-color state labels
- [x] 6.8 Add phone, tablet and desktop responsive tests for pending confirmation and screenshot reachability
- [ ] 6.9 Add visual checks for safe-area devices, long translated text, zoom and narrow landscape layouts

## 7. Documentation and Verification

- [x] 7.1 Update the user guide for categorized materials, empty selection and main-region live actions
- [x] 7.2 Update `docs/user-journey.md` with the optional-material preparation path
- [x] 7.3 Verify no real resume, JD, screenshot or interview content is introduced into fixtures or tests
- [x] 7.4 Run protocol and Web typechecks, unit tests, integration tests and production builds
- [ ] 7.5 Run mobile keyboard, screen-reader, touch-target and drawer interaction reviews
- [x] 7.6 Validate `refine-interview-materials-and-mobile-actions` with OpenSpec strict mode
- [x] 7.7 Review every capability scenario against the implemented prototype before marking the change complete
