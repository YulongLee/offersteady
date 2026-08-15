## 1. Main-process screenshot lock

- [x] 1.1 Implement and unit-test the screenshot lock state machine
- [x] 1.2 Apply the lock to manual capture, remote capture, and global shortcut entry points with failure release
- [x] 1.3 Add preload IPC for reading, observing, and cancelling the authoritative lock

## 2. Companion user interface

- [x] 2.1 Synchronize renderer state with the main-process lock
- [x] 2.2 Disable screen selection and repeat preview while locked, and add a visible “取消当前截屏” action
- [x] 2.3 Update desktop copy regression tests for locked, cancelled, and retryable behavior

## 3. Verification

- [x] 3.1 Run desktop tests, typecheck, production build, diff checks, and strict OpenSpec validation
