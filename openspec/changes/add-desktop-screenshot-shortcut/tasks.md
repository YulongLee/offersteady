## 1. Desktop shortcut settings

- [x] 1.1 Add supported shortcut presets and local preference persistence
- [x] 1.2 Register and replace Electron global shortcuts with conflict rollback
- [x] 1.3 Add shortcut selection and status feedback beside screen capture controls

## 2. Authorized screenshot trigger

- [x] 2.1 Add a device-scoped backend endpoint guarded by the active live binding
- [x] 2.2 Reuse the existing remote capture, upload, vision answer, and failure pipeline
- [x] 2.3 Prevent overlapping shortcut requests in desktop and backend layers

## 3. Live page integration

- [x] 3.1 Synchronize completed shortcut screenshot answers into the current live workspace
- [x] 3.2 Deduplicate task IDs and stop synchronization for inactive pages
- [x] 3.3 Add pure regression coverage for supported shortcut validation
- [x] 3.4 Display shortcut screenshot progress and terminal failure state immediately
