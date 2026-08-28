## 1. Desktop Voice-Aware Endpointing

- [x] 1.1 Add deterministic system-audio regressions for speech followed by above-floor residual energy, short-pause continuation, quiet-speech admission, and maximum-turn safety.
- [x] 1.2 Implement bounded temporal voice evidence so residual program energy cannot refresh meaningful system speech indefinitely while preserving current microphone behavior.
- [x] 1.3 Preserve 100-millisecond incremental publication, pre-speech retention, terminal priority, and content-free boundary diagnostics.

## 2. Backend Partial And Terminal Path

- [x] 2.1 Add regressions proving unseen provider revisions publish independently before commit and terminal admission remains immediate.
- [x] 2.2 Tighten the provider partial hot path without adding synchronous append waits or moving cold work ahead of SSE publication.

## 3. Web Visible Completion

- [x] 3.1 Add regressions proving committing freezes the latest partial without active caret or client-inferred incomplete, while authoritative final/incomplete reconcile monotonically.
- [x] 3.2 Remove age-derived incomplete presentation and render committing as a stable background-confirming state without changing the approved layout.

## 4. Companion 1.2.10

- [x] 4.1 Increment all companion version metadata to 1.2.10 while preserving layout, icon, identity, endpoints, signing, and permission behavior.
- [x] 4.2 Run Desktop, Backend, Web, protocol, typecheck, production-build, and strict OpenSpec verification; document any unrelated existing failures.
- [x] 4.3 Build/package the Apple Silicon 1.2.10 companion and verify metadata/signing without publishing production artifacts.

## 5. Local Physical Acceptance

- [x] 5.1 Launch an isolated local Backend and Web chain plus the 1.2.10 companion without disturbing production or unrelated local sessions.
- [x] 5.2 Confirm the local endpoints and companion process are ready, then hand off first-partial and stopped-utterance physical testing to the user.

## 6. Production Rollout

- [x] 6.1 Re-run release-critical verification and strict OpenSpec validation against the exact rollout tree.
- [x] 6.2 Build and verify the versioned 1.2.10 Apple Silicon, Intel macOS, and Windows x64 production artifacts.
- [x] 6.3 Upload versioned desktop artifacts and atomically update the production download manifest without exposing incomplete targets.
- [ ] 6.4 Commit and push the reviewed release baseline, retain production Backend/Web rollback images, and deploy only the changed application services without recreating PostgreSQL or Redis.
- [ ] 6.5 Verify public health, Web build manifest, download metadata/artifacts, realtime endpoints, and record the production release evidence.
