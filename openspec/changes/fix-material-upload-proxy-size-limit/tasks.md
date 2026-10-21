## 1. Gateway boundary

- [x] 1.1 Add a route-scoped 21 MB Nginx request-body allowance for resume, job-description, and knowledge proxy uploads.
- [x] 1.2 Add a deployment configuration regression test proving supported upload routes are covered and unrelated APIs are not globally widened.

## 2. Error accuracy

- [x] 2.1 Preserve HTTP 413 through the upload adapter and present an upload-size error instead of a generic object-storage error.
- [x] 2.2 Keep failed optimistic uploads classified as upload failures rather than parser failures, with focused Web regression coverage.

## 3. Verification and production hotfix

- [x] 3.1 Run focused Web tests, build validation, Nginx syntax validation, and strict OpenSpec validation.
- [x] 3.2 Apply the scoped config to Chinese production, gracefully reload only Nginx, and verify the upload endpoint accepts a synthetic request larger than 1 MB without touching Backend, database, Redis, interviews, or Global.
- [x] 3.3 Persist the hotfix in the deployable Web image and record rollback/verification evidence.

## Production evidence (2026-09-06 CST)

- `nginx -t`: successful before reload.
- Reload: `nginx -s reload` on `compose-web-1`; Backend, PostgreSQL, Redis, Admin and Analytics were not restarted.
- Synthetic 1.5 MiB raw body to `/api/v1/resume/uploads/proxy`: HTTP 422 from Backend validation; a 1.5 MiB multipart upload reached Backend authentication and returned HTTP 401. Both prove Nginx no longer rejects the upload as 413.
- The same 1.5 MiB multipart probe through `https://www.mianshiwen.cn` returned HTTP 401 and public `/healthz` returned HTTP 200.
- Identical body to unrelated `/api/v1/web/state`: HTTP 413, proving the allowance is not global.
- `/healthz`: HTTP 200 after reload.
- Rollback image: `compose-web:before-material-upload-20260906` (`sha256:7e1d60a5fce5...`).
- Persisted image: `compose-web:material-upload-20260906` (`sha256:fb933c4f8074...`), also tagged `compose-web:latest`.

## 4. 2026-10-21 runtime gateway follow-up

- [x] 4.1 Record that the active gateway lacks the repository's upload-specific rule; preserve all historical production evidence without treating it as current verification.
- [x] 4.2 Add a baseline-SHA-pinned, pure preparation tool that inserts only the material proxy envelope and refuses conflicts, drift and overwrite.
- [x] 4.3 Run focused regressions proving byte preservation, routing isolation, failure guards and the exact Backend 20MiB file boundary.
- [x] 4.4 Reproduce HTTP413 with the old missing-rule config in an isolated Nginx; verify synthetic20MiB multipart on all three routes,21MiB overflow and unchanged unrelated limits.
- [x] 4.5 Freshly pin the actual production Web config/image, pass complete user-work gates, prepare and syntax-check the exact runtime-derived candidate and persist its fixed image through the combined authorized release.
- [x] 4.6 Verify actual active gateway config, unchanged public JS/assets and non-target components after release; record actual deployment, independent verification and rollback readiness without creating production documents.
- [x] 4.7 Append actual public unauthenticated upload-boundary probes and short-lived redacted error observations with their measured window; do not infer them from deployment success.

Local verification: [2026-10-21 upload boundary](../../../docs/releases/cn-upload-20m-local-20261021.md). Frontend generic failure wording remains outside this follow-up.

Production: [2026-10-22 actual cutover](../../../docs/releases/cn-upload20m-model1017-20261021.1.md), deployed2026-10-22 00:30:56.856CST; r2`deploy-3` and independent`verify-1` exit0. Prior two deploy attempts deferred atTCP1 without switching. Actual public probes returned proxy422/unrelated413 with transport success and no document/model work;75.6-second observation ended00:38:52.180CST with all three components running/restart0 and zeroERROR/traceback/HTTP5xx, without tail truncation.
