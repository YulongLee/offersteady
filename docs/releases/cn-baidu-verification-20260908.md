# Domestic Baidu verification maintenance — 2026-09-08

Added owner-supplied `codeva-Z0cblvEvbJ` verification meta inside homepage head, preserving existing `codeva-QBTtniJaXE`. No title/body/script/style or business changes.

- Updated main workspace and production-baseline worktree `apps/web/index.html` (worktree `/private/tmp/offersteady-cn-release-20260907.DTlvCc`). No other workspace code deployed.
- Production release remains `/opt/offersteady/releases/20260907-cn-home-downloads-1`, app version unchanged. Updated its source index and atomically replaced only the running Web container's built index.
- Persisted exact HTML layer in image `compose-web:baidu-verification-20260908` (`a735bbd4fed4`), also tagged `compose-web:latest`. Running container retains its original image ID and updated writable HTML layer; no containers recreated/restarted. Next compose recreation uses the updated image; future rebuild uses updated source.
- Before publication: zero desktop transports, workers, queued frames, live answer active/pending, screenshot activity, and live interview sessions active within 30 minutes. Stale session rows untouched.
- Source and built HTML byte-diff tests passed: removing exactly the single added meta line restores each original file byte-for-byte. Existing verification token and assets/body preserved.
- Public curl requests to `https://mianshiwen.cn/`, both ordinary and simulated `Baiduspider`, returned the exact expected HTML without executing JavaScript. Both SHA256 values: `6b798ee9a90e85b59f393c332373de3895f626e204b32df789d6fb1dee3f1b5f`. Source-loopback response matches too.
- All eight container IDs identical before and after. No international changes. No full application test suite rerun for this HTML-only maintenance.
- Evidence and scripts: local `/private/tmp/cn-baidu-meta.RMeXYb/`; server `/tmp/cn-baidu-meta-20260908/`.

## Rollback

Retained original image: `compose-web:baidu-before-20260908` (`a16580fd9824`). Server directory above contains `source.backup.html` and `index.backup.html`. If rollback is authorized, restore those exact files via staged atomic replacement and retag the original image as `compose-web:latest`. No database changes to undo.

The owner must click Baidu's verification button; successful crawler simulation does not establish that Baidu has accepted site ownership.
