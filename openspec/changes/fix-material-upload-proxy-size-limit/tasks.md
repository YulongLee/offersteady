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
