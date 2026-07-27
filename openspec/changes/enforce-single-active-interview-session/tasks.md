## 1. Contract and backend enforcement

- [x] 1.1 Define active-session conflict and explicit takeover API contracts
- [x] 1.2 Reject direct device binding and session start when another live session exists
- [x] 1.3 Retire old bindings, publishers, ASR queues, and web heartbeats during takeover

## 2. Web preparation experience

- [x] 2.1 Load authoritative conflict state before enabling device connection
- [x] 2.2 Add continue-previous and end-previous conflict actions
- [x] 2.3 Preserve existing materials and last-device connection choices after takeover

## 3. Desktop lifecycle and regression coverage

- [x] 3.1 Include binding generation in the desktop realtime connection identity
- [x] 3.2 Add regression coverage for explicit takeover before device binding
- [x] 3.3 Document deployment and compatibility boundaries without changing unrelated features
