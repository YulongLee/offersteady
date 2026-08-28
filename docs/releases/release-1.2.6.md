# Release 1.2.6 Local Acceptance

Release 1.2.6 adds a privacy-local preparation sound check and prevents an opened-but-silent source from being reported as ready. It preserves the approved companion layout and icon while changing the existing microphone and computer-output cards to show explicit check guidance and fresh real-signal status.

## Included

- Separate track-open state from fresh microphone and computer-output signal evidence.
- Expire signal readiness after 120 seconds and invalidate it after track mute/end or callback stall.
- Promote only fresh checked preparation streams into live capture; independently reopen stale sources.
- Retain a bounded pre-speech window and add a varying-energy low-volume system speech path without treating steady digital noise as speech.
- Add a compatible Web preparation gate with a third “声音检查” readiness item and Backend runtime readiness based on fresh signal evidence.
- Preserve production endpoints, bundle identifier `com.offersteady.companion`, protocol 2.0, approved transparent icon, and the 1.2.4 visual layout.

## Privacy

Preparation PCM remains local and memory-only. No preparation audio is uploaded, transcribed, persisted, billed, or included in diagnostics. Only source state, level, and timestamps are reported.

## Acceptance Boundary

The local Apple Silicon application points to the production Web and Backend. Until the compatible Web and Backend changes are separately deployed, physical acceptance can validate the companion sound-check cards, low-volume detector, warm-source behavior, and existing production compatibility, but the production preparation page will not yet enforce the new three-step gate.

## Rollback

Before installation, preserve the existing 1.2.5 application under `/Applications/OfferSteady Rollbacks/`. Restoring that application rolls back the local desktop behavior without changing production services.
