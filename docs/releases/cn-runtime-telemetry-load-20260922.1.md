# Domestic runtime telemetry load reduction — 2026-09-22

## Scope

This release reduces diagnostic traffic that was inflating ordinary API P95 during live interviews. It does not change ASR, transcription, answer generation, screenshot assistance, billing, session state, or the desktop companion protocol.

## Changes

- Non-final transcript-render telemetry is sampled at most once per session window; final revisions remain reported.
- Transcript-render acknowledgements reuse a bounded, short-lived ownership check instead of rereading the full session and bound materials for every sample.
- Per-ack diagnostic logging is no longer emitted at INFO level.
- The Web client and Backend retain their existing request and response contracts.

## Verification

- Backend telemetry and capacity tests: 21 passed.
- Web backend-adapter tests: 35 passed.
- Web typecheck: passed.
- Production Web build: passed.
- Backend Python compilation: passed.
- `openspec validate reduce-runtime-telemetry-load --strict`: passed.
- Production gate: database `live` interview count was 0 immediately before switch.
- Public `/healthz` and `/api/v1/web/state`: HTTP 200 after switch.
- Post-switch Backend logs: no ERROR or CRITICAL entries in the verification window.

## Deployment and rollback

- Domestic release directory: `/opt/offersteady/releases/20260922-cn-telemetry-p0-1`.
- Previous release retained: `/opt/offersteady/releases/20260922-cn-realtime-reclamation-1`.
- Rollback marker: `/opt/offersteady/.cn_rollback_20260922_telemetry_p0`.
- Only Backend and Web containers were recreated. Database, Redis, Admin, analytics and material-worker containers were left running.
