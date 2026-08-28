## Why

Live acceptance shows that audio reaches the realtime path, but users still experience multi-second first text, system-audio turns that usually end by the eight-second safety limit, and visible turns that keep waiting for provider finalization. The product must present the newest recognized words while speech is ongoing and make a stopped utterance feel complete without waiting on the provider's authoritative final.

## What Changes

- Preserve the current persistent dual-channel realtime architecture while tightening the hot path from incremental audio to provider partial to SSE to browser paint.
- Replace system-output release decisions based primarily on instantaneous RMS with source-specific temporal voice evidence, adaptive noise context, hysteresis, and bounded silence release; retain RMS as a fallback and maximum duration only as a safety boundary.
- Keep incremental audio publication at a bounded cadence and publish every new provider revision independently from append/final work.
- Decouple visible utterance completion from provider finalization: terminal admission freezes the latest partial immediately, while authoritative final reconciliation continues in the background.
- Remove browser-age inference of `incomplete`; only an authoritative Backend terminal state may present an incomplete utterance.
- Add content-free timing and boundary acceptance evidence for first partial, partial cadence, endpoint release, terminal ACK, provider final, and browser presentation.
- Increment the companion to 1.2.10, preserve its approved layout, transparent icon, identity, permission model, production endpoints, and rollback behavior, and launch an isolated local acceptance chain after automated verification.
- Non-goals: adding local transcript storage, changing answer prompts, redesigning Web or companion UI, replacing DashScope in this iteration, or claiming physical Intel macOS/Windows acceptance from the local Apple Silicon test.

## Capabilities

### New Capabilities

- `perceived-realtime-transcript-delivery`: Continuous visible partial delivery, voice-aware system endpointing, immediate visible terminal admission, authoritative background reconciliation, and measurable commercial latency gates.

### Modified Capabilities


## Impact

- Desktop speech segmenter, source diagnostics, version/package metadata, and deterministic audio-boundary tests.
- Backend realtime provider partial publication, terminal lifecycle evidence, and regression tests.
- Web transcript presentation state and progressive transcript tests.
- Local Backend/Web/Apple Silicon companion launch and physical acceptance handoff.
- After explicit user acceptance, a reversible production rollout of Backend, Web, and versioned 1.2.10 companion artifacts.
- No raw PCM, transcript text, credentials, or personal data is added to diagnostics or persisted by this change.
