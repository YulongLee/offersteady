## Verification Summary

Date: 2026-08-09

### Automated checks

- Backend targeted remote screenshot tests: 5 passed.
- Backend full suite: 166 passed, 6 skipped, 1 existing Starlette/httpx deprecation warning.
- Desktop full suite: 43 passed.
- Web full suite: 166 passed.
- Remaining npm workspace suites: Admin 10, API 90 and Protocol 27 passed.
- Workspace typecheck passed.
- Desktop and Web production builds passed; Web keeps the existing bundle-size warning.
- SEO P0 routing checks passed.
- `openspec validate fix-desktop-idle-polling-and-add-legal-pages --strict` passed.
- Nginx 1.27 configuration test passed.
- Local production-style Nginx returned HTTP 200 and `X-Robots-Tag: noindex, follow` for `/terms` and `/privacy`.
- Regression route matrix kept `/`, `/login`, `/app`, `/app/library`, `/app/billing`, `/app/devices`, `/app/settings` and `/error` at HTTP 200 while an unknown route remained HTTP 404.

One concurrent full-suite run observed the pre-existing 10 ms timer race in `test_gateway_receives_partial_on_background_pump_and_reuses_connection`. The same ASR test passed five consecutive isolated runs, and the complete Backend suite then passed on rerun. The affected screenshot, desktop and Web changes do not import or modify the ASR gateway.

### Production rollout checklist

1. Deploy Backend first and confirm old idle clients receive HTTP 200 with `data: null` from the next-capture endpoint.
2. Compare the next-capture request rate and `desktop-capture-binding` warning count for at least 30 minutes; expected idle warnings are zero.
3. Confirm PostgreSQL logs contain no new deadlocks attributable to desktop heartbeat or screenshot polling.
4. Deploy Web/Nginx and verify `https://mianshiwen.cn/terms` and `/privacy` return 200, `noindex, follow`, CSP, HSTS, `nosniff` and `DENY` headers.
5. Verify login and homepage footer links open both documents without authentication.
6. Publish the rebuilt desktop package only after a live-device test proves: idle state does not query next-capture, entering a live session starts screenshot polling promptly, one screenshot is claimed once, and hiding the window does not create a second poller.
7. Retain the previous desktop package for rollback. Backend empty-result compatibility and legal pages do not require rollback if the desktop package is withdrawn.

### Remaining external review

- The user agreement and privacy policy reflect the current documented product behavior but still require professional legal review before broad commercial release.
- Production monitoring and real-device rollout checks remain pending until deployment is explicitly authorized.
