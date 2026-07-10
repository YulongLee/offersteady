## 1. Preparation page readiness logic

- [x] 1.1 Audit current preparation-page start gating, completion count, blocked help copy, and tests that reference “问题输入方式”
- [x] 1.2 Change Web start readiness so confirmed material selection is the only required condition for entering the live workspace
- [x] 1.3 Replace the blocking “问题输入” checklist item with non-blocking local-companion/input diagnostics copy
- [x] 1.4 Ensure entering live workspace without audio readiness does not automatically start microphone, system audio, or automatic question detection

## 2. Local companion diagnostics boundary

- [x] 2.1 Confirm existing companion/device status fields can express disconnected, permission-required, degraded, and manual/screenshot fallback states
- [x] 2.2 Update UI copy so users understand local software checks收音、系统音频和问题检测, while Web can still enter the interview
- [x] 2.3 If backend session start currently checks input readiness, relax it to validate only user ownership, session state, and confirmed material selection

## 3. Tests and documentation

- [x] 3.1 Add or update frontend tests proving confirmed materials enable “开始面试” even when local companion/audio input is unavailable
- [x] 3.2 Add or update tests proving unconfirmed or invalid material selection still blocks “开始面试”
- [x] 3.3 Update user journey, prototype baseline or guide docs that still say users must prepare an input method before entering interview
- [x] 3.4 Run focused Web tests, Web typecheck, relevant backend tests if touched, and `openspec validate streamline-interview-start-readiness --strict`
