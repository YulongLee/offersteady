## 1. Initialization Loading

- [x] 1.1 Make saved-session restoration the sole protected-state loader and prevent the public loader race.
- [x] 1.2 Add regressions for valid session, no session, slow restore and final initialization failure without transient backend-error rendering.
- [x] 1.3 Replace visible technical loading copy with a theme-matched silent transition while retaining accessible status semantics.

## 2. Appearance Preference Model

- [x] 2.1 Add a typed appearance preference module with defaults, allowlist parsing, safe localStorage reads/writes and root attribute application.
- [x] 2.2 Apply stored appearance preferences before the first React render and add malformed/unavailable-storage tests.

## 3. Settings and Live Workspace

- [x] 3.1 Convert answer font size to a controlled setting that applies immediately and persists across refreshes.
- [x] 3.2 Add a controlled dark/bright theme setting with clear labels and immediate persistence.
- [x] 3.3 Replace live-answer fixed sizes with scoped variables and add complete bright-theme colors for the app shell, live workspace, forms, cards and overlays.
- [x] 3.4 Add Web component/style regressions for settings controls, font-size scope, theme application and responsive layouts.
- [x] 3.5 Restore visible danger-button and disabled-button contrast in the bright theme, including hover and keyboard-focus states.

## 4. Verification

- [x] 4.1 Run focused and full Web tests, typecheck, production build, diff checks and strict OpenSpec validation.
- [x] 4.2 Confirm no Backend, database, desktop companion or AI prompt/eval changes are required.
- [x] 4.3 Run the bright-theme contrast regression, full Web verification and production-build checks.
