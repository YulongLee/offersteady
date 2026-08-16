## 1. Desktop preview interaction

- [x] 1.1 Remove the persistent screen preview row from the companion main window
- [x] 1.2 Add an on-demand preview dialog with immediate loading, image/video, error, close, and cleanup states
- [x] 1.3 Keep the preview control stable while preserving in-flight screenshot mutual exclusion
- [x] 1.4 Remove the user-facing cancel action and automatically release preview and task locks
- [x] 1.5 Remove the redundant bottom completion control from the preview dialog

## 2. Styling and regression coverage

- [x] 2.1 Add responsive dialog styles and remove obsolete persistent preview styles
- [x] 2.2 Add regression coverage for hidden-by-default preview, manual dialog behavior, and in-flight locking
- [x] 2.3 Update regression coverage for stable preview wording and automatic lock release
- [x] 2.4 Add regression coverage that the preview dialog has no bottom completion button

## 3. Verification

- [x] 3.1 Run desktop tests, type checking, and production build
- [x] 3.2 Run strict OpenSpec validation and review the packaged UI behavior
- [x] 3.3 Re-run desktop verification and publish the corrected synchronized installers
- [x] 3.4 Verify and publish the simplified preview dialog across all desktop installers
