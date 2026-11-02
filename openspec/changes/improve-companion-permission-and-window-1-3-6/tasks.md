## 1. Baseline and contract

- [x] 1.1 Verify actual CN runtime, commit/push and tag current source/static snapshot before any companion changes.
- [x] 1.2 Record approved local-only scope, visibility override, permission/audio/package scenarios and apply-ready design.

## 2. Permissions and mock readiness

- [x] 2.1 Implement truthful structured OS permission IPC and deduplicated current late-result handling without false timeout denial or Windows fake grant.
- [x] 2.2 Synchronize changed capabilities promptly and coalesce registrations; keep existing heartbeat and mode isolation, with mock microphone-only UI/checks.
- [x] 2.3 Add permission timing, lifecycle, classification and registration regressions.

## 3. Mock microphone lifecycle

- [x] 3.1 Require current running context within bounded resume; detect ended/interrupted input, fence and release with explicit retry.
- [x] 3.2 Cover stale sockets/epochs/media callbacks, transient mute, context failure, pause/end and unchanged buffers/backoff.

## 4. Explicit window visibility

- [x] 4.1 Add unified all-hide/restore controls for window/Dock/taskbar/tray, application reopen and conflict-aware restore shortcut.
- [x] 4.2 Preserve latest intent during ready/recovery/Dock races and test no duplicate capture or automatic hidden relaunch.

## 5. Local package and handoff

- [x] 5.1 Bump desktop and lock to1.3.6; run relevant/full desktop tests, typecheck/build and independent scope review.
- [x] 5.2 Build installable Mac and Windows local packages with CN defaults; verify architecture, frozen dist, actual signature/entitlements and no unintended config/keys.
- [x] 5.3 Exercise isolated synthetic window/permission recovery where feasible, document hardware/notarization limits, provide local installation links without production or distribution updates.

Executed validation and local installer handoff: [companion1.3.6 local](../../../docs/releases/companion-1.3.6-local-20261101.md). No production, official download manifest, OSS, Global distribution or new companion source push.

## 6. User acceptance correction — same1.3.6, local-only

- [x] 6.1 Remove new standalone recheck/notice presentation while preserving existing error retry and permission/audio fixes.
- [x] 6.2 Retain fixed-size transparent Tray, direct left-click restore and right-click menu; update visibility regressions and tooltip.
- [x] 6.3 Run full tests/typechecks and actual Mac transparent image/bounds/native menu verification; attempt pointer click and record tool/hardware limits; independent review.
- [x] 6.4 Rebuild/verify three same-version installers serially as Local-r2, preserve source/payload evidence and provide corrected local packages without publishing.

修订验证与本地交付见[同版本r2记录](../../../docs/releases/companion-1.3.6-local-r2-20261101.md)。用户实体设备验收待完成；未授权发布，后续通过后再按用户指令处理。
