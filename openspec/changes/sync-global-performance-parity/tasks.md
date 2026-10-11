## 1. Candidate implementation

- [x] 1.1 Extract the actual running Global backend source/image and create an isolated candidate overlay.
- [x] 1.2 Apply the five-field web-heartbeat projection and preserve lifecycle semantics.
- [x] 1.3 Apply bounded desktop-heartbeat write coalescing and its configuration default.

## 2. Verification

- [x] 2.1 Add and run regression tests for web heartbeat I/O, desktop coalescing, and Global request-breakdown fields.
- [x] 2.2 Run focused static checks and `openspec validate sync-global-performance-parity --strict`.
- [x] 2.3 Build the candidate Global backend image from the actual running Global release and run an isolated container smoke test.

## 3. Global deployment

- [x] 3.1 Obtain two consecutive Global idle-gate confirmations before changing the running service.
- [x] 3.2 Deploy only the Global backend, then verify health, release markers, capacity fields, and public manifest.
- [x] 3.3 Record release evidence and the rollback image/tag.
