## 1. Desktop Continuous Segmentation

- [x] 1.1 Add synthetic segmenter regressions for short pauses, source-specific finalization, interim revision identity, and maximum turn duration.
- [x] 1.2 Keep microphone and system speech on stable segment IDs through normal pauses while preserving 100 ms interim snapshots and bounded memory.
- [x] 1.3 Bump companion versions and release metadata for every supported platform without changing permissions or capture ownership.

## 2. Backend Realtime Transcript and Question Context

- [x] 2.1 Add Backend regressions for interim upserts, final revision identity, adjacent trusted interviewer context, role boundaries, and duplicate-trigger prevention.
- [x] 2.2 Ensure provider-timed interim revisions remain publishable and build automatic question text from the latest bounded trusted interviewer turn.

## 3. Web Conversation Turns

- [x] 3.1 Add pure Web tests for revision reconciliation, safe same-role joining, role changes, long gaps, overlaps, and contributing source IDs.
- [x] 3.2 Render continuous transcript revisions and safe residual fragments as one progressive conversation turn while preserving pending-question controls.
- [x] 3.3 Reuse the bounded interviewer-turn projection for quick-answer fallback text.

## 4. Verification and Release

- [x] 4.1 Run focused and full Desktop, Web, and Backend tests, type checks, production builds, privacy review, and strict OpenSpec validation.
- [x] 4.2 Build and inspect supported companion artifacts and verify release manifest URLs, checksums, architectures, and versions.
- [ ] 4.3 Commit and push the approved change to Git.
- [ ] 4.4 Deploy only affected Backend/Web services, publish companion artifacts without restarting unrelated services, and verify production health and downloads.
