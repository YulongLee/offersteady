## 1. Backend device and lease model

- [x] 1.1 Add a durable account-device association and last-used-device representation compatible with existing desktop registrations
- [x] 1.2 Add authenticated APIs to read the last usable device and connect a session by machine code or last device
- [x] 1.3 Make session connection idempotent and atomically revoke conflicting user/device leases without deleting durable device association
- [x] 1.4 Return independent permission, presence, account-binding and session-connection states from desktop status APIs

## 2. Web interview connection experience

- [x] 2.1 Detect whether an interview is newly created or historical without changing the existing preparation-page visual structure
- [x] 2.2 Keep machine-code entry for new interviews and add last-device reconnect plus alternate machine-code entry for historical interviews
- [x] 2.3 Remove browser permission implications and map disconnected session state to connection copy rather than authorization copy
- [x] 2.4 Handle lease takeover, offline last device and duplicate connection responses with actionable states

## 3. Desktop state separation

- [x] 3.1 Keep stable device identity and report macOS permission status independently from the active interview binding
- [x] 3.2 Update assistant status presentation so granted permissions remain visible while the assistant waits for an interview connection
- [x] 3.3 Ensure a new session lease starts one capture supervisor and an ended or replaced lease stops only session capture
- [x] 3.4 Simplify connection management to a fixed code plus direct interview action and remove the redundant status-detail panel
- [x] 3.5 Give the main app and native capture helper stable local code requirements and bind permission usage metadata to the helper executable

## 4. Verification and release

- [x] 4.1 Add backend regression tests for durable association, last-device reconnect, lease takeover and state separation
- [x] 4.2 Add Web tests for new-interview machine-code connection and historical-interview connection choices
- [x] 4.3 Add desktop tests for permission and session-state separation
- [x] 4.4 Run focused backend, Web and desktop tests plus strict OpenSpec validation
- [x] 4.5 Enforce terminal realtime revocation for replaced sessions and stop stale Web reconnect loops
- [ ] 4.6 Build the macOS arm64 assistant, commit and push the completed change, then deploy backend and Web to production
