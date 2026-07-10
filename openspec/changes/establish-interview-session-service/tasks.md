## 1. Session domain and lifecycle foundation

- [x] 1.1 Define Interview Session domain models, lifecycle states, and repository contracts
- [x] 1.2 Define session material binding, configuration snapshot, conversation context, and usage record models
- [x] 1.3 Replace the current placeholder session module boundary with a concrete session service module plan

## 2. Session APIs and state orchestration

- [x] 2.1 Design create, detail, list, continue, end, and restart session API contracts
- [x] 2.2 Design APIs for confirming session materials and reading session-scoped configuration snapshots
- [x] 2.3 Design APIs for appending conversation context and reading recoverable context windows

## 3. Integration boundaries and verification

- [x] 3.1 Define session references for Retrieval, Answer, Screenshot, Desktop Bridge, and Billing integrations without coupling implementation details
- [x] 3.2 Define token usage recording and query boundaries at session scope
- [x] 3.3 Run `openspec validate establish-interview-session-service --strict`
