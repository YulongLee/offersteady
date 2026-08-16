## 1. Desktop preview interaction

- [x] 1.1 Remove the persistent screen preview row from the companion main window
- [x] 1.2 Add an on-demand preview dialog with immediate loading, image/video, error, close, and cleanup states
- [x] 1.3 Keep the preview control stable while preserving in-flight screenshot mutual exclusion
- [x] 1.4 Remove the user-facing cancel action and automatically release preview and task locks

## 2. Styling and regression coverage

- [x] 2.1 Add responsive dialog styles and remove obsolete persistent preview styles
- [x] 2.2 Add regression coverage for hidden-by-default preview, manual dialog behavior, and in-flight locking
- [x] 2.3 Update regression coverage for stable preview wording and automatic lock release

## 3. Verification

- [x] 3.1 Run desktop tests, type checking, and production build
- [x] 3.2 Run strict OpenSpec validation and review the packaged UI behavior
- [x] 3.3 Re-run desktop verification and publish the corrected synchronized installers
