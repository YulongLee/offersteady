## Why

Production acceptance on 1.2.10 shows that visible partials stream correctly, but the last words of an utterance can still arrive two to four seconds after speech stops because local endpointing, terminal scheduling, and provider completion remain sequential tail-latency boundaries. The existing DashScope model must be retained while OfferSteady minimizes every application-controlled delay and preserves transcript completeness.

## What Changes

- Replace fixed end-of-speech release behavior with bounded source-specific adaptive tails that end clear silence sooner without splitting ordinary pauses or quiet trailing speech.
- Make the last audio append and provider commit an explicitly ordered, priority path that cannot wait behind replaceable partial work or cold-path business processing.
- Continue publishing every monotonic provider partial received after terminal admission, so trailing words appear before authoritative provider completion whenever available.
- Harden Web reconciliation so post-commit partials append immediately, shorter hypotheses do not retract visible text, and provider final remains authoritative.
- Add privacy-safe tail timing and text-length-delta diagnostics plus deterministic and real-provider acceptance gates.
- Evaluate a short synthetic-silence flush behind a disabled-by-default feature flag; enable it only if isolated measurements improve tail latency without accuracy or segmentation regression.
- Increment the companion patch version to 1.2.11 while preserving layout, icon, identity, permissions, endpoints, protocol compatibility, and privacy defaults.
- Non-goals: replacing DashScope, adding a second or on-device ASR model, redesigning either UI, changing prompts, billing, capture permissions, or transcript/audio persistence.

## Capabilities

### New Capabilities

- `bounded-provider-tail-delivery`: Adaptive local release, ordered priority commit, post-commit partial delivery, monotonic browser reconciliation, and measurable speech-end-to-last-visible-text behavior on the existing provider.

### Modified Capabilities


## Impact

- Desktop audio segmenter, terminal transport ordering, feature flags, diagnostics, tests, and 1.2.11 package metadata.
- Backend realtime ingress scheduling, DashScope commit/final lifecycle, transcript event publication, metrics, and regression tests.
- Web transcript reconciliation and presentation tests without layout or user-facing recovery changes.
- Local Apple Silicon companion acceptance against the unchanged online service after automated verification; Intel macOS and Windows receive equivalent code/build validation without claiming unperformed physical acceptance.
- Diagnostics remain content-free and no raw PCM, transcript text, credentials, or personal data is newly persisted.
