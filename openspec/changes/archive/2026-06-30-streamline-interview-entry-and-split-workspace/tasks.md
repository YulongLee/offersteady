## 1. Reconcile Active Specifications

- [x] 1.1 Revise `add-web-interview-application` so preparation no longer requires a generic data-purpose checkbox
- [x] 1.2 Revise `add-web-interview-application` so settings do not offer an unsupported interview-record retention preference
- [x] 1.3 Revise `add-web-interview-application` live workspace requirements from side panels to the new split workspace
- [x] 1.4 Revise `add-per-interview-context-selection` to limit material changes to the pre-interview preparation flow
- [x] 1.5 Revise `refine-interview-materials-and-mobile-actions` to remove the data-purpose confirmation from start prerequisites
- [x] 1.6 Revise `simplify-live-interview-workspace` to remove the material rail and replace the vertical desktop regions with resizable columns
- [x] 1.7 Update `docs/user-journey.md` and in-app guidance with the single continuation action, pre-start material confirmation and split workspace
- [x] 1.8 Validate every reconciled active change before editing implementation behavior
- [x] 1.9 Reconcile the single continuation action with `optimize-product-experience-and-distribution`

## 2. Single Interview Continuation

- [x] 2.1 Define one state-to-route resolver for preparing, live, paused, recoverable and ended interviews
- [x] 2.2 Replace “继续准备” and “预览工作台” with one “继续面试” dashboard action
- [x] 2.3 Keep the interview status label and progress copy distinct from the invariant action label
- [x] 2.4 Restore the saved preparation state when “继续面试” routes to a preparing interview
- [x] 2.5 Route an in-progress or recoverable interview directly to the live workspace
- [x] 2.6 Add dashboard tests proving there is exactly one continuation action and no preview action
- [x] 2.7 Add route tests for preparing, live and recoverable session states

## 3. Aligned Material Selection and Start Gate

- [x] 3.1 Derive preparation candidates from the same account-scoped library source collection used by the materials page
- [x] 3.2 Share material type, version, processing, failure and deletion state mappings between the materials page and picker
- [x] 3.3 Preserve zero-or-one resume, zero-or-one JD and zero-to-many knowledge selection cardinality
- [x] 3.4 Disable processing, failed, deleted and unauthorized sources without creating replacement picker records
- [x] 3.5 Detect an invalidated saved selection and require explicit reconfirmation without silently substituting another source
- [x] 3.6 Keep confirmed empty and partial selections valid preparation outcomes
- [x] 3.7 Remove the generic `privacyConfirmed` checkbox from the preparation interface and start readiness calculation
- [x] 3.8 Replace the checkbox with concise non-interactive usage, audio-default and deletion disclosure near “开始面试”
- [x] 3.9 Keep manual mode free from implicit microphone or system-audio activation
- [x] 3.10 Preserve action-specific audio permission and screenshot preview confirmation flows
- [x] 3.11 Remove or compatibility-isolate stale `privacyConfirmed` protocol, fixture and persisted-state fields
- [x] 3.12 Add integration tests covering aligned source lists, failed sources, deleted selections, empty confirmation and start readiness
- [x] 3.13 Add privacy regression tests proving start does not authorize audio and screenshots are not submitted before confirmation

## 4. Simplified Session Data Controls

- [x] 4.1 Remove the interview-record retention-period selector and its 7-day, 30-day and manual-delete options from settings
- [x] 4.2 Keep the truthful “原始音频默认不保存” status visible in settings
- [x] 4.3 Add a settings link to session data management or the relevant usage guide without inventing an automatic expiry promise
- [x] 4.4 Preserve review-page screenshot deletion and whole-interview deletion operations
- [x] 4.5 Preserve server-confirmed success, failure and retry states for deletion
- [x] 4.6 Add settings tests proving no retention form control or unsupported duration copy is rendered
- [x] 4.7 Add review regression tests for successful and failed deletion paths

## 5. Live Workspace Structure

- [x] 5.1 Remove the live material rail, collapse control, drawer entry and related session-storage state
- [x] 5.2 Remove the live “调整资料” command while retaining the confirmed selection revision for answer requests
- [x] 5.3 Keep actual answer source names and versions visible in `AnswerWorkspace`
- [x] 5.4 Place `ConversationMonitor` in the left desktop column
- [x] 5.5 Place `AnswerWorkspace`, answer history controls and `CompactQuestionBar` in the right desktop column
- [x] 5.6 Ensure layout changes reuse one instance of each business component without resetting transcripts, answer position, drafts or screenshot tasks
- [x] 5.7 Add workspace structure tests proving the material rail is absent and source provenance remains available

## 6. Resizable and Accessible Columns

- [x] 6.1 Add a versioned session-scoped split-ratio state keyed by interview ID
- [x] 6.2 Validate stored ratios and fall back to the default for invalid, stale or out-of-range values
- [x] 6.3 Implement min-width-aware ratio clamping from the live workspace container dimensions
- [x] 6.4 Implement pointer capture, move, release and cancellation behavior for the divider
- [x] 6.5 Coalesce high-frequency pointer updates without mutating interview business state
- [x] 6.6 Add vertical separator semantics, accessible value bounds, current value and visible focus styling
- [x] 6.7 Implement Arrow, Shift+Arrow, Home and End keyboard adjustments
- [x] 6.8 Implement an accessible default-ratio reset action
- [x] 6.9 Respect reduced-motion preferences while resizing
- [x] 6.10 Add ratio utility tests for defaulting, clamping, persistence and session isolation
- [x] 6.11 Add component tests for pointer dragging, pointer cancellation, keyboard controls and reset behavior
- [x] 6.12 Add regression tests proving streaming updates during resize do not duplicate answers or clear action state

## 7. Responsive Layout and Interaction Review

- [x] 7.1 Define the desktop breakpoint and verified minimum widths for conversation and answer columns
- [x] 7.2 Hide and remove the divider from the accessibility tree below the desktop breakpoint
- [x] 7.3 Stack live conversation, answer and compact actions in that order on tablet and phone
- [x] 7.4 Restore the valid session split ratio when returning from narrow to desktop layout
- [x] 7.5 Preserve answer history position, transcript scroll intent, draft text and screenshot state across breakpoint changes
- [x] 7.6 Verify compact actions remain reachable above phone safe areas and the on-screen keyboard
- [x] 7.7 Verify no horizontal overflow at representative phone, tablet, 1200px and 1440px widths

## 8. Verification and Handoff

- [x] 8.1 Update Web tests that currently expect “继续准备”, “预览工作台”, the privacy checkbox, retention selector or material rail
- [x] 8.2 Use only synthetic interview, transcript, answer and material fixtures in new tests
- [x] 8.3 Run all protocol, API, desktop and Web tests
- [x] 8.4 Run workspace typechecks and production builds
- [x] 8.5 Run browser interaction review for continuation, preparation, settings, pointer resize, keyboard resize and narrow fallback
- [x] 8.6 Check Markdown links and run strict validation for this change and every reconciled active change
- [x] 8.7 Review each capability scenario against implemented behavior and record any intentionally deferred open question
