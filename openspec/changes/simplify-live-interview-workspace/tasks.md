## 1. Spec Reconciliation and View State

- [x] 1.1 Reconcile the two-region layout with `add-web-interview-application` three-column requirements
- [x] 1.2 Reconcile inline question confirmation with `add-speaker-role-detection`
- [x] 1.3 Reconcile the compact no-price action bar with `refine-interview-materials-and-mobile-actions`
- [x] 1.4 Reconcile hidden live point labels with active billing and cost-disclosure specs
- [x] 1.5 Define material-rail, answer-page and new-answer-available view state types
- [x] 1.6 Add stable answer ID pagination helpers independent of array insertion order
- [x] 1.7 Add unit tests for view-state migration from the existing live workspace

## 2. Collapsible Material Rail and Focused Layout

- [x] 2.1 Replace the desktop three-column grid with a collapsible material rail and one main workspace
- [x] 2.2 Add accessible “收起资料” and “展开资料” controls with `aria-expanded`
- [x] 2.3 Persist material-rail state by interview session in `sessionStorage`
- [x] 2.4 Expand the main workspace immediately when the material rail is collapsed
- [x] 2.5 Remove the permanent right-side history, transcript and device column
- [x] 2.6 Move compact device and capture status into the live top bar
- [x] 2.7 Preserve material adjustment, privacy copy and empty-context state in the collapsible rail
- [x] 2.8 Add reduced-motion behavior for rail width changes
- [x] 2.9 Add layout tests proving current answer and input state survive rail toggles

## 3. Real-Time Conversation Region

- [x] 3.1 Refactor `SpeakerPanel` into the main-region `ConversationMonitor`
- [x] 3.2 Render interviewer and candidate segments chronologically with time and role labels
- [x] 3.3 Distinguish interim, final, overlap and uncertain transcript states with text
- [x] 3.4 Update streaming revisions in place using stable segment ID and revision
- [x] 3.5 Follow new conversation only when the user is already near the bottom
- [x] 3.6 Move low-confidence question confirm and ignore actions onto the related conversation item
- [x] 3.7 Keep role-correction controls available without recreating a right sidebar
- [x] 3.8 Ensure confirmed interviewer questions create one answer task
- [x] 3.9 Ensure candidate speech, acknowledgements and duplicate revisions create no answer task or usage
- [x] 3.10 Add AI/speaker evaluation cases for interviewer triggers and candidate false-trigger rejection
- [x] 3.11 Add conversation rendering, revision, confirmation and deduplication tests

## 4. Answer Workspace and History Pagination

- [x] 4.1 Build `AnswerWorkspace` for current and historical answers
- [x] 4.2 Add previous, next, position/total and “回到最新” controls
- [x] 4.3 Derive pagination from stable answer IDs rather than mutable array indexes
- [x] 4.4 Preserve each historical answer's original question, sources, revision and uncertainty state
- [x] 4.5 Keep the selected history page stable when a new answer is inserted
- [x] 4.6 Show a non-disruptive “有新答案” state while history is open
- [x] 4.7 Disable unavailable page directions with accessible explanations
- [x] 4.8 Remove the old history-list selection and right-drawer history entry
- [x] 4.9 Add boundary, insertion, return-to-latest and provenance regression tests

## 5. Compact Question and Screenshot Bar

- [x] 5.1 Replace the large `LiveActionComposer` card with `CompactQuestionBar`
- [x] 5.2 Place a bounded auto-growing manual input beside “回答问题” and “截图回答”
- [x] 5.3 Disable “回答问题” for empty input with an accessible reason
- [x] 5.4 Submit manual questions through the existing idempotent answer pipeline
- [x] 5.5 Open the existing screenshot preview flow without clearing the manual draft or answer page
- [x] 5.6 Remove point and membership labels from live automatic, manual and screenshot controls
- [x] 5.7 Remove point totals from screenshot action labels while preserving failure and retry states
- [x] 5.8 Preserve server-side balance validation, usage IDs, settlement and release behavior
- [x] 5.9 Show insufficient-balance recovery without falsely entering a generating state
- [x] 5.10 Keep current balance, rates and ledger details discoverable on the billing page
- [x] 5.11 Add compact-bar, no-live-price-label, idempotency and insufficient-balance tests

## 6. Responsive and Accessible Interaction

- [x] 6.1 Stack conversation, answer and compact input in the same order on tablet and phone
- [x] 6.2 Convert the material rail to a phone/tablet drawer without adding a history drawer
- [x] 6.3 Keep pagination and both action buttons reachable above safe-area and session controls
- [x] 6.4 Handle the mobile on-screen keyboard using dynamic viewport or visual viewport behavior
- [x] 6.5 Keep phone touch targets at least 44×44 CSS pixels while retaining compact desktop styling
- [x] 6.6 Preserve transcript scroll, selected answer ID, input draft and screenshot task across breakpoint changes
- [x] 6.7 Add keyboard order, accessible labels, status announcements and non-color state cues
- [x] 6.8 Add phone, tablet, desktop, zoom, long-text and narrow-landscape checks
- [x] 6.9 Run screen-reader, soft-keyboard, touch-target and drawer interaction reviews

## 7. Documentation and Verification

- [x] 7.1 Update the in-app guide for the two-region live workspace and answer pagination
- [x] 7.2 Update `docs/user-journey.md` with interviewer-first answering and compact actions
- [x] 7.3 Verify fixtures and tests contain only synthetic or desensitized conversation content
- [x] 7.4 Run protocol and Web typechecks, unit tests, integration tests and production builds
- [x] 7.5 Validate all reconciled active changes with OpenSpec strict mode
- [x] 7.6 Review every focused-workspace capability scenario against the implemented prototype
