## 1. Frontend Foundation

- [ ] 1.1 Resolve the four open UX questions in `design.md` and record the approved device roles
- [ ] 1.2 Select the frontend framework, styling approach and component test tooling used by the MVP application
- [ ] 1.3 Define shared color, spacing, typography, radius, breakpoint and interaction tokens from the design direction
- [ ] 1.4 Create synthetic interview, question, answer, document-status and connected-device fixtures

## 2. Desktop Page Prototype

- [ ] 2.1 Implement the desktop top bar with interview identity, connection state and account actions
- [ ] 2.2 Implement the document-status rail for resume, JD, knowledge base and screenshot entry
- [ ] 2.3 Implement the current-question and real-time-answer panel with loading, streaming, complete and failed states
- [ ] 2.4 Implement the history and connected-device rail with collapsible behavior
- [ ] 2.5 Implement the persistent session-control bar for pause, manual question and end actions
- [ ] 2.6 Add visual snapshots at desktop and intermediate breakpoints using synthetic data

## 3. Mobile Companion Prototype

- [ ] 3.1 Implement the mobile connection header and current-question card
- [ ] 3.2 Implement the answer-outline view with expandable full answer and source details
- [ ] 3.3 Implement touch-friendly pause, resume and screenshot actions
- [ ] 3.4 Implement the mobile navigation between live view, materials and history
- [ ] 3.5 Verify layout continuity when crossing responsive breakpoints without losing local UI state
- [ ] 3.6 Add mobile visual snapshots and touch-target accessibility checks

## 4. Shared Session Model

- [ ] 4.1 Define typed session snapshot, event, command, device-role and connection-state contracts
- [ ] 4.2 Implement the authoritative server-side session state and monotonically increasing event version
- [ ] 4.3 Implement unique command IDs and idempotent command processing
- [ ] 4.4 Connect desktop and mobile pages to a shared client session store
- [ ] 4.5 Add contract tests for snapshots, event ordering, duplicate commands and conflicts

## 5. Device Pairing and Authorization

- [ ] 5.1 Implement discovery of active sessions for devices using the same authenticated account
- [ ] 5.2 Implement short-lived one-time pairing tokens represented as a QR code and 6-digit code
- [ ] 5.3 Build desktop pairing, pending-device and device-removal interactions
- [ ] 5.4 Build mobile code entry, pairing confirmation, expiration and rejection states
- [ ] 5.5 Prevent unpaired or removed devices from receiving session content
- [ ] 5.6 Add security tests for invalid, expired, reused and revoked pairing credentials

## 6. Realtime Synchronization and Recovery

- [ ] 6.1 Implement a replaceable bidirectional session transport and connection-status reporting
- [ ] 6.2 Synchronize session, current-question, answer-increment, document-status, screenshot-task and device-list events
- [ ] 6.3 Implement reconnect using the client’s last confirmed event version
- [ ] 6.4 Implement missing-event replay with full-snapshot fallback
- [ ] 6.5 Prevent duplicated question or answer content after retries and reconnections
- [ ] 6.6 Add integration tests for two-device updates, event order, network interruption and snapshot recovery

## 7. Primary Input Device

- [ ] 7.1 Display the current primary input device on all connected clients
- [ ] 7.2 Implement a confirmed role-transfer flow that stops the previous device before activating the next
- [ ] 7.3 Block automatic capture attempts from secondary devices while preserving explicit screenshot and manual-question actions
- [ ] 7.4 Add concurrency tests for simultaneous takeover requests and unexpected primary-device disconnects

## 8. Verification and Handoff

- [ ] 8.1 Verify keyboard navigation, focus visibility, screen-reader labels and non-color status indicators
- [ ] 8.2 Verify that notifications, page titles and unauthorized screens do not expose sensitive interview content
- [ ] 8.3 Run responsive end-to-end tests for desktop-only, mobile-only and paired-device journeys
- [ ] 8.4 Verify the two capability specs scenario by scenario and record evidence for deferred items
- [ ] 8.5 Update project documentation with final frontend commands, device roles and synchronization architecture
