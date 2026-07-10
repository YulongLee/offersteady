## 1. Web Application Foundation

- [x] 1.1 Add the selected client router and define typed public and protected route constants
- [x] 1.2 Refactor the existing single page into public-site and authenticated-app layouts
- [x] 1.3 Define shared design tokens, responsive breakpoints and accessible focus styles
- [x] 1.4 Define domain interfaces for interview summaries, preparation status, live sessions and reviews
- [x] 1.5 Build a fixture adapter using only synthetic interview and document data
- [x] 1.6 Add route-level error, loading, unauthorized and not-found boundaries

## 2. Public Entry and Application Shell

- [x] 2.1 Build the public product page with workflow, platform-role and privacy explanations
- [x] 2.2 Build the login entry and a development-only prototype identity flow
- [x] 2.3 Implement protected route handling that does not render sensitive page data before authorization
- [x] 2.4 Build desktop navigation for interviews, library, devices and settings
- [x] 2.5 Build mobile navigation with at least 44×44 CSS pixel primary touch targets
- [x] 2.6 Build the action-oriented application home for new, returning and active-session states
- [x] 2.7 Add shell navigation, authorization, keyboard and responsive component tests

## 3. Interview Creation and Preparation

- [x] 3.1 Build the new-interview form with name, target role and optional company fields
- [x] 3.2 Implement draft creation, validation, confirmed-save indication and safe restoration
- [x] 3.3 Build the preparation checklist for resume, JD, knowledge base, device and privacy states
- [x] 3.4 Build resume and JD upload cards with parsing, inspection, replacement, retry and deletion states
- [x] 3.5 Build the optional knowledge-base summary and material-management entry
- [x] 3.6 Integrate the existing desktop companion download, pairing and diagnostic card into the devices route and preparation page
- [x] 3.7 Implement personalized-ready, limited-demo and manual-mode readiness rules
- [x] 3.8 Build the pre-start sensitive-data disclosure and explicit confirmation control
- [x] 3.9 Add preparation tests for missing, processing, ready, failed, replaced and deleted context

## 4. Live Interview Workspace Layout

- [x] 4.1 Build the wide-screen three-column workspace with fixed session controls
- [x] 4.2 Build collapsible document, question-history and device supporting panels
- [x] 4.3 Build the tablet layout with drawer-based supporting panels
- [x] 4.4 Build the mobile single-column live view with bottom navigation and one-hand controls
- [x] 4.5 Preserve current question, streamed answer, scroll position and session state across responsive layout changes
- [x] 4.6 Add visual-regression and interaction tests at desktop, tablet and mobile breakpoints

## 5. Live Questions and Answer Advice

- [x] 5.1 Define the live-question and answer-presentation state models
- [x] 5.2 Build current-question states for listening, transcribing, confirmed, uncertain and failed input
- [x] 5.3 Build streamed answer advice with outline, expanded detail, source types and uncertainty presentation
- [x] 5.4 Visually and semantically separate original material, model inference and generated advice
- [x] 5.5 Build historical-question navigation without replacing the active-question state
- [x] 5.6 Implement safe retry and return-to-current-answer behavior
- [x] 5.7 Add synthetic AI evaluation cases that reject invented employers, projects, responsibilities and metrics
- [x] 5.8 Add answer-state component tests for generation, streaming, uncertainty, failure and recovery

## 6. Explicit Input and Session Controls

- [x] 6.1 Integrate confirmed desktop audio and device-status events behind the existing protocol boundary
- [x] 6.2 Build manual question input and command-ID duplicate protection
- [x] 6.3 Build the in-workspace screenshot picker, preview, confirmation and removal flow
- [x] 6.4 Build screenshot upload, recognition, classification, answer and failure states
- [x] 6.5 Implement start, pause, resume and confirmed-end session commands
- [x] 6.6 Build offline, reconnecting, device-disconnected and permission-denied recovery notices
- [x] 6.7 Ensure page titles, notifications and client logs exclude sensitive question and answer content
- [x] 6.8 Add tests for duplicate inputs, screenshot cancellation, offline controls and end-session transitions

## 7. Review and Data Controls

- [x] 7.1 Build the ended-interview summary and chronological confirmed-question list
- [x] 7.2 Build the lightweight AI review area with waiting, generating, complete, failed and retry states
- [x] 7.3 Keep raw question records, answer advice and AI-generated review in separate labelled sections
- [x] 7.4 Build per-screenshot deletion with pending, confirmed and failed states
- [x] 7.5 Build whole-interview deletion and explain the retention of reusable source documents
- [x] 7.6 Clear affected query caches and local presentation data only after confirmed deletion
- [x] 7.7 Add authorization, empty-review, failed-generation and deletion tests

## 8. API Integration and End-to-End Verification

- [x] 8.1 Define replaceable API adapters for interview drafts, preparation state, live snapshots, events and reviews
- [ ] 8.2 Replace fixtures page by page while retaining fixtures for Storybook-style and automated states
- [x] 8.3 Implement cancellation, retry and error normalization without logging sensitive payloads
- [x] 8.4 Verify external AI, speech, OCR, parsing and retrieval credentials remain server-side
- [x] 8.5 Run the complete desktop journey from public entry through create, prepare, live, end and review
- [x] 8.6 Run the mobile companion journey for viewing, pausing, screenshot submission and reconnecting
- [x] 8.7 Run keyboard, screen-reader naming, contrast and touch-target accessibility checks
- [x] 8.8 Verify all specification scenarios with synthetic or redacted data and document deferred behavior
