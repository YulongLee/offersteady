## Why

Production evidence shows that an interviewer utterance can remain permanently marked as “transcribing” when its system-audio final result is suppressed as a cross-channel duplicate after the microphone copy finalizes first. Because automatic answering only accepts finalized system-audio questions, this stale partial also prevents the user from receiving an answer during the interview.

## What Changes

- Make cross-channel deduplication role-aware so the system-audio final remains authoritative for interviewer speech even when a microphone echo final arrives first.
- Reconcile or retire the matching non-final transcript whenever a final result is suppressed, so no visible row can remain indefinitely in “transcribing”.
- Add a bounded stale-partial recovery path that closes abandoned partial rows without fabricating speech or charging for an answer.
- Add regression coverage for the exact production ordering: system partial, microphone final, system final, cross-channel deduplication.
- Preserve the existing ASR provider, public realtime APIs, privacy policy, and dual-channel UI.

## Capabilities

### New Capabilities

- `realtime-transcript-finalization-recovery`: Defines authoritative channel selection, partial/final reconciliation, and bounded recovery when an ASR final event is suppressed or missing.

### Modified Capabilities

None.

## Impact

- Backend realtime transcript processing and cross-channel duplicate suppression.
- Web live-conversation projection and stale partial presentation.
- Realtime regression tests and synthetic dual-channel fixtures.
- No raw audio persistence, new external dependency, public API break, or desktop capture permission change.
