# Release 1.2.11 realtime tail and ASR provider switch

Release 1.2.11 combines the approved source-aware tail latency changes with a protocol-correct adapter for `qwen-audio-3.0-asr-flash-streaming`. It preserves the 1.2.10 companion layout, icon, product identity, permissions, capture ownership, public Web routes, and realtime protocol 2.0.

## Realtime changes

- Clear post-speech silence uses bounded source-specific release targets: 280 ms for microphone and 220 ms for system audio, while ambiguous/noisy tails keep conservative ceilings.
- Backend terminal work is coalesced and prioritized without overtaking previously admitted PCM.
- Post-commit provider revisions remain visible and shorter non-final hypotheses no longer erase longer visible text; authoritative final correction remains allowed.
- Content-free terminal queue, provider tail, and final-added-character timing fields are available for diagnosis.
- The optional Qwen3 manual-commit silence suffix remains disabled by default.

## Qwen Audio 3 provider path

- `OFFERSTEADY_REALTIME_ASR_PROTOCOL=qwen-audio-task` selects the new inference-task adapter.
- `qwen-audio-3.0-asr-flash-streaming` uses `wss://dashscope.aliyuncs.com/api-ws/v1/inference` with `run-task`, binary PCM, `result-generated`, and `finish-task`.
- The prior `qwen3-realtime` adapter and public `/api-ws/v1/realtime` endpoint remain an explicit rollback tuple.
- Workspace-specific inference remained unavailable with HTTP 403 `Endpoint.AccessDenied`; no Workspace endpoint is selected for this release.

## Verification

- Desktop: 166 tests passed; typecheck, build, and macOS Apple Silicon, macOS Intel, and Windows x64 packaging passed.
- Qwen Audio adapter/legacy protocol focused suites: 23 tests passed.
- Backend full suite: 350 passed and 14 skipped. Two pre-existing load-sensitive timing assertions failed under the loaded run and passed immediately in isolated reruns.
- Web realtime focused suite: 46 tests passed; typecheck and guarded production build passed. One pre-existing unrelated material-action assertion remains stale.
- Protocol: 31 tests passed; typecheck and build passed.
- Live adapter synthetic-audio verification returned five revisions and the correct final text, with the first partial observed at approximately 656 ms from local test start.
- Both active OpenSpec changes and `git diff --check` passed.

## Production rollout and rollback

Deploy Backend/Web from this release commit, then change the server-side provider tuple and restart Backend only:

```text
OFFERSTEADY_REALTIME_ASR_PROTOCOL=qwen-audio-task
OFFERSTEADY_REALTIME_ASR_MODEL=qwen-audio-3.0-asr-flash-streaming
OFFERSTEADY_REALTIME_ASR_INFERENCE_WS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/inference
```

Rollback restores `qwen3-realtime`, `qwen3-asr-flash-realtime-2026-02-10`, and `wss://dashscope.aliyuncs.com/api-ws/v1/realtime`, then restarts Backend. PostgreSQL and Redis volumes must not be deleted or recreated.
