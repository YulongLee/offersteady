# Global quick-answer admission pilot 2026-09-07.1

- Host: `47.84.65.103`
- Release: `global-quick-answer-pilot-20260907.1`
- Release path: `/opt/offersteady-global/releases/20260907-global-quick-answer-pilot-1`
- Scope: Global Backend and Global Web only
- Database migrations: none
- Chinese production deployment: none

The release moves synchronous live-answer generation to an isolated bounded executor, adds content-free route/admission/generator timing, and renders the first non-empty Global answer chunk immediately. Model, Prompt, RAG, billing, cancellation, history, ASR, screenshot answer and Companion behavior are unchanged.

## Verification

- Backend: 538 passed, 21 skipped.
- Global Web: 53 passed; strict English-copy audit, typecheck and production build passed.
- OpenSpec and Global deployment-asset validation passed.
- Before cutover: Global live interviews 0, active desktop transports 0, active realtime workers 0 and queued frames 0.
- After cutover: public health, live-answer status and build manifest passed; Backend/Web restart count 0; recent Backend error count 0.
- Production executor smoke preserved ordered frames and released its capacity.
- Chinese public health remained `ok`; no Chinese container or source deployment was performed.

## Rollback

The preceding source release remains `/opt/offersteady-global/releases/20260907-global-members-1`. Pre-cutover images are retained as:

- `offersteady-global-backend:rollback-before-quick-answer-pilot-20260907`
- `offersteady-global-web:rollback-before-quick-answer-pilot-20260907`

Rollback must recreate only Global Backend/Web from those images and must not restart Global PostgreSQL/Redis or any Chinese production service.
