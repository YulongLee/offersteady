## 1. Desktop Boundary Regressions

- [x] 1.1 Add deterministic microphone regressions for steady noise, short transients, sustained quiet speech, and retained first syllables.
- [x] 1.2 Add deterministic system-output regressions for steady low-level noise, quiet speech variation, bounded first admission, and prompt tail finalization.
- [x] 1.3 Add warm-handoff regressions for calibration metadata transfer, expiry/invalidation, and no preparation PCM publication.

## 2. Desktop Implementation And 1.2.7

- [x] 2.1 Implement bounded source calibration and multi-evidence speech admission without adding content-bearing diagnostics.
- [x] 2.2 Transfer fresh calibration into the live segmenter and preserve independent stale-source fallback.
- [x] 2.3 Add privacy-safe first-speech and terminal boundary diagnostics while preserving transport compatibility.
- [x] 2.4 Increment companion metadata to 1.2.7 and preserve approved layout, icon, identity, endpoints, and signing configuration.

## 3. Backend Bounded Finalization

- [x] 3.1 Add regressions for two-second manual-final completion, missing-completion incomplete recovery, no same-terminal retry, and other-source continuity.
- [x] 3.2 Implement bounded provider-final recovery that preserves the latest visible partial and closes only the affected source.
- [x] 3.3 Set production-safe explicit manual commit, finalization budget, and 2.5-second watchdog defaults with backward compatibility.
- [x] 3.4 Expose content-free finalization stage/recovery evidence and verify no transcript/audio payload enters diagnostics.

## 4. Web Readiness And Terminal Presentation

- [x] 4.1 Add regressions for production audio readiness gating, manual-only entry, confirming timeout, and stable incomplete terminal presentation.
- [x] 4.2 Complete the compatible three-step sound gate and monotonic terminal presentation without changing the approved layouts.

## 5. Verification And Production Rollout

- [x] 5.1 Run focused and full Desktop, Backend, Web, protocol, typecheck, build, and strict OpenSpec validation suites.
- [x] 5.2 Record production Backend/Web/companion rollback baselines and verify deploy prerequisites without exposing secrets.
- [x] 5.3 Deploy Backend then Web, verify health/config compatibility and public smoke checks, and retain rollback artifacts.
- [x] 5.4 Build, sign, install, and reopen Apple Silicon companion 1.2.7 for user acceptance; report cross-platform physical acceptance limits truthfully.

## 6. Automatic Preparation And Prompt Live Promotion

- [x] 6.1 Remove the mandatory Web sound gate and its test controls; restore material-plus-bound-device entry with automatic background preparation.
- [x] 6.2 Add regressions for silent preparation and a sub-500-millisecond bound-companion live control transition.
- [x] 6.3 Tighten the bound preparation control interval without changing VAD, endpointing, privacy, or provider model behavior.
- [x] 6.4 Run focused/full Web and Desktop verification, production builds, and strict OpenSpec validation; deploy the Web update and prepare the updated companion for physical acceptance.

## 7. Background Companion Activation

- [x] 7.1 Add a regression proving the companion disables Electron background renderer throttling while retaining the 250-millisecond preparation control interval.
- [ ] 7.2 Disable background throttling, increment the companion to 1.2.9, build/sign/install it, and repeat physical start-to-publisher timing acceptance.

## 8. Live Binding Stability And Truthful Reconnect State

- [x] 8.1 Add Backend regressions proving a pinned active connection remains selected and another account cannot displace a live device binding.
- [x] 8.2 Add Desktop regressions for pinned active-connection polls, non-alarming initial startup, missing source bootstrap health, and genuine post-healthy recovery.
- [x] 8.3 Implement Backend pinned-binding selection and live-device conflict protection without breaking older clients.
- [x] 8.4 Implement Desktop session pin lifecycle and truthful reconnect-state transitions without changing the approved layout.
- [x] 8.5 Run focused/full Backend and Desktop verification, typechecks, production builds, strict OpenSpec validation, and build/sign the Apple Silicon 1.2.9 acceptance app.
- [ ] 8.6 Launch the isolated local Backend/Web/companion chain and repeat the physical binding-stability and first-visible acceptance test with the user.
