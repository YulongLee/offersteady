# Global homepage pricing 2026-09-07.1

- Host: `47.84.65.103`
- Release: `global-homepage-pricing-20260907.1`
- Release path: `/opt/offersteady-global/releases/20260907-global-homepage-pricing-1`
- Baseline: `/opt/offersteady-global/releases/20260907-global-homepage-film-1`
- Scope: Global Web only
- Database migrations: none
- Backend, Admin, worker, PostgreSQL, Redis, Companion and China deployment changes: none

The release adds the canonical Global price table to the homepage after Core Capabilities and before Responsible Assistance. It shows Free, Interview Day Pass, Pro Weekly, Pro Monthly, and Job Hunt, highlights the canonical featured plan, and links visitors to `/login` or `/pricing`. The homepage does not initiate checkout and does not change any plan, payment, or entitlement behavior.

## Verification

- Scoped baseline comparison showed only the approved homepage catalogue lookup, pricing markup, and responsive styles.
- Global Web: 55 tests passed; focused product test 49 passed; English-copy audit, typecheck, production build, and strict OpenSpec validation passed.
- Before cutover: recent live interviews 0, active desktop transports 0, active realtime workers 0, and queued frames 0. The same gate remained clear immediately before Web recreation.
- Public build marker reports `global-homepage-pricing-20260907.1`.
- A JavaScript-executing production DOM check rendered all five plan names, four paid prices, the pricing headline, supporting message, `/login`, and `/pricing` links.
- The public `/pricing` page still exposes all approved prices, Global and China health checks pass, and the Global Web error count after deployment is zero.
- Only Global Web was recreated. Global Backend, Admin, PostgreSQL, and Redis retained their container IDs, start times, and zero restart counts.

## Rollback

The preceding release remains `/opt/offersteady-global/releases/20260907-global-homepage-film-1`. The pre-cutover Web image is retained as `offersteady-global-web:rollback-before-homepage-pricing-20260907`.

Rollback must restore the preceding `current` symlink and recreate only Global Web from the retained image. It must not restart Global Backend, Admin, workers, PostgreSQL, Redis, Companion, or any China production service.
