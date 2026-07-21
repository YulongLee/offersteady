## 1. Persistent Account and History

- [x] 1.1 Implement a PostgreSQL authentication repository for users, identity bindings, auth sessions, and SMS challenges.
- [x] 1.2 Select PostgreSQL authentication persistence whenever the backend has a database configuration.
- [x] 1.3 Return the authenticated user's complete non-deleted interview history from Web state.

## 2. Device and Material Consistency

- [x] 2.1 Keep desktop device identity and derived machine code stable across concurrent initialization and normal application lifecycle events.
- [x] 2.2 Replace dashboard hard-coded material values with counts derived from backend material records.
- [x] 2.3 Distinguish ready, processing, and total material counts without exposing document content.

## 3. Commercial Persistence Boundary

- [x] 3.1 Reject missing PostgreSQL configuration for production authentication, interview, and material repositories.
- [x] 3.2 Preserve explicit dependency failures instead of silently reporting successful in-memory persistence in production.
- [x] 3.3 Run targeted persistence regression tests and strict OpenSpec validation when validation is approved.
