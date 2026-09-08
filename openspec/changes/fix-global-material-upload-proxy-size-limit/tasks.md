## 1. Global gateway

- [x] 1.1 Add a route-scoped 21 MB allowance to the Global Web Nginx configuration.
- [x] 1.2 Extend the gateway regression test to cover both editions without widening unrelated APIs.

## 2. Global client accuracy

- [x] 2.1 Map proxy HTTP 413 to an English 20 MB file-size validation error.
- [x] 2.2 Label pre-registration upload failures separately from parser failures and add focused tests.

## 3. Verification

- [x] 3.1 Run Global focused tests, production build, Nginx syntax validation and strict OpenSpec validation.
- [ ] 3.2 Deploy the English client copy in the next controlled Global Web release. The two scoped Nginx layers are already live and verified with a synthetic multipart upload larger than 1 MB.

## Production gateway evidence (2026-09-06 CST)

- Inner Global Web Nginx and public host Nginx both passed `nginx -t` before graceful reload.
- A 1.5 MiB multipart request through `https://offersteady.com/api/v1/resume/uploads/proxy` returned HTTP 401 from Backend authentication instead of HTTP 413.
- An equally large request to unrelated `/api/v1/web/state` remained HTTP 413.
- Public `/healthz` remained HTTP 200; Backend, Admin, Analytics, PostgreSQL and Redis were not restarted.
- Rollback image: `offersteady-global-web:before-material-upload-20260906` (`sha256:07bf9217cde4...`).
- Persisted gateway image: `offersteady-global-web:material-upload-20260906` (`sha256:06da97455771...`), also tagged `offersteady-global-web:latest`.
- Host Nginx rollback file: `/etc/nginx/sites-available/offersteady-global.before-material-upload-20260906`.
