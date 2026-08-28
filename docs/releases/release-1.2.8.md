# Release 1.2.8 Automatic Preparation And Prompt Live Promotion

Release 1.2.8 removes the mandatory preparation sound gate. Binding the companion now remains the only explicit audio preparation action: local sources open and calibrate without publishing preparation PCM, while the Backend prewarms both realtime ASR channels.

The bound companion checks the preparation-to-live control transition every 250 milliseconds, reducing the interval before already-open sources are promoted into the live publisher. VAD, endpointing, model selection, audio persistence, and the approved companion layout remain unchanged.

## Acceptance

- A silent user can start after materials are confirmed and the companion is bound.
- The preparation page does not show test-voice or Mac speech controls.
- The Backend prewarms microphone and system provider channels while the session is preparing.
- A bound companion polls the waiting live transition at no more than 250 milliseconds.
- Only post-live admitted audio is published; preparation audio remains local and ephemeral.
