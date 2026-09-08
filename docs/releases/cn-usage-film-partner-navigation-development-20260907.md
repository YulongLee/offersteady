# Chinese usage film and partner navigation

Implemented in the domestic production-baseline worktree `/private/tmp/offersteady-cn-release-20260907.DTlvCc`. The main workspace lacks the deployed domestic partner implementation and must not replace it.

Changes: added a separate narrated usage video after the homepage workflow, retained the existing promotional film, and added links to `/app/partner-program` in the public header and desktop/mobile workbench navigation. Existing dashboard enrollment and paused-activity restrictions remain authoritative. Navigation visibility intentionally supersedes the former bottom-only discovery decision per the user's latest request.

Video: original 49-second 1920×1080 H.264/AAC, 6,813,765 bytes, copied with its poster to versioned `/media/device-story-voice-20260907.mp4` and `/media/device-story-poster-20260907.jpg`. Native controls, default muted, inline playback and metadata preload; no autoplay.

Verification: partner and product-experience regression suites passed (26 tests), TypeScript and production build passed, strict OpenSpec validation passed. Responsive CSS was reviewed; a real-browser visual acceptance has not been completed.

Status: deployed to domestic production at approximately 2026-09-07 13:47 CST as `cn-usage-film-partner-nav-20260907.1`. Source change: `add-cn-usage-film-and-partner-navigation` in the domestic worktree. Only Web was recreated.

Deployment requested on 2026-09-07. Around 13:40 CST, current domestic release was confirmed as `/opt/offersteady/releases/20260907-cn-quick-answer-film-1`. App.tsx and styles.css differ only by the intended video and navigation edits. Scoped overlay prepared at `/private/tmp/cn-usage-film-partner-nav-20260907.tgz`. Deployment remains pending: one non-deleted live session exists (last activity around 12:45), although desktop transports and answer executors report zero. No session was ended, no container restarted and no production files changed. Resume with a fresh occupancy check; the overlay does not itself authorize ending stale sessions.

Subsequent deployment: user confirmed no ongoing interviews. Before build and cutover, recent live sessions (30-minute activity window), desktop transports, audio workers/frames, active/pending quick answers and screenshot streams were all zero. The stale session row was preserved. Release directory `/opt/offersteady/releases/20260907-cn-usage-film-partner-nav-1`; current symlink points there. Rollback image `compose-web:rollback-before-usage-film-20260907`, previous release retained. Deployment script `/private/tmp/deploy-cn-usage-film-20260907.sh`.

Production checks: build marker matches, health is OK with unchanged backend version, Nginx config passes, video and poster HTTP 200, video range request HTTP 206/1024 bytes. Video SHA256 `3125873b44570177f29d5c138abf9a9debcf2a5b6fcb735e33e7cd7d0a33211a` matches original H.264/AAC source. Served JS includes tutorial and partner navigation markers. Backend/admin/Postgres/Redis/material-worker/analytics/promotion-analytics container IDs and start times unchanged. Initial local health probe experienced a connection reset during Web startup, then passed. No global deployment performed. Build reported existing dependency engine/audit warnings; no dependency upgrades were attempted in this scoped release.
