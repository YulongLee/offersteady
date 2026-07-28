## 1. Persistence Guards

- [x] 1.1 Remove authentication fallback to memory when a database URL is configured
- [x] 1.2 Remove billing fallback to memory when a database URL is configured
- [x] 1.3 Preserve explicit in-memory construction for isolated tests and database-free prototypes

## 2. Regression Coverage

- [x] 2.1 Add a regression test proving authentication fails closed on database connection failure
- [x] 2.2 Add a regression test proving billing fails closed on database connection failure
- [x] 2.3 Retain persistent welcome-grant restart and duplicate-credit coverage

## 3. Operations

- [x] 3.1 Document PostgreSQL as the authoritative account and points ledger
- [x] 3.2 Document that database volumes must not be removed during deployment
