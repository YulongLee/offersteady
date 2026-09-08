# OfferSteady Global English product boundary

Status: Global Web is deployed; strict 1.2.15 companion parity update implemented and verified locally, companion installers not yet published

## Application boundary

| Surface | Global scope | Isolation rule |
| --- | --- | --- |
| Public website and authentication | English customer experience | Built from `apps/web-global`; never replaces `apps/web` |
| Interview and written-exam workflows | English preparation, live guidance, screenshot answers, review, and export | Uses the existing API contract; Global sessions default to `en-US` |
| Materials, devices, settings, help, and billing presentation | English customer experience | International providers and prices remain deployment configuration |
| Desktop companion | Additive Global profile | Separate identity, endpoints, update channel, and artifacts |
| Administration | Chinese | `apps/admin` is not translated or replaced |

## Route inventory

The Global application retains the current application route families:

- Public application routes: landing, sign-in, public guide, pricing, terms, privacy, refund policy, contact, about, and security. Merchant-review routes have independent static initial HTML as well as React routes. Legacy invitation URLs only redirect to the public entry flow.
- Account: sign-in/registration shell, account menu, device list, appearance, and support.
- Interview: list, creation, preparation, material selection, language/programming preferences, device pairing, live transcript, manual and quick answer, Auto Answer, screenshot answer, completion, review, and Word export.
- Written exam: list, creation, companion pairing, screenshot-only answer workflow, completion, review, and deletion.
- Materials: resumes, job descriptions, knowledge collections/documents, upload, processing, quote, indexing, rename, download, enable/disable, reprocess, and delete.
- Commercial presentation: credit balance, membership, usage rates, ledger history, and support guidance. Referral campaigns and domestic checkout are not part of the Global product.

## Global commerce boundary

Global commerce is disabled by default with `VITE_GLOBAL_COMMERCE_PROVIDER=none` and `VITE_GLOBAL_COMMERCE_ENABLED=false`. The customer application does not render or invoke Alipay, WeChat Pay, QR checkout, domestic catalogues, or referral APIs. Legacy `/invite/:code` links redirect to the normal public entry flow without resolving or activating the code.

The future Creem change will use `VITE_GLOBAL_COMMERCE_PROVIDER=creem` only as a public presentation selector. Creem API keys and webhook secrets remain in the Backend environment. The Backend will create checkout sessions, associate provider objects with internal user/order identifiers, verify raw webhook signatures, store provider event IDs for idempotency, and atomically apply credits or entitlements. A browser success redirect is never sufficient to grant value. Test and live credentials/products remain isolated.

Before payment activation, the public `/pricing` page displays only Free (`$0`), Weekly Pro (`$19.99/week`), and Monthly Pro (`$39.99/month`). Free links to account registration; both paid offers are labelled `Coming Soon` and do not call checkout.

## Merchant-review public disclosure

The Global public operator is `杭州临平知界智能技术工作室（个体工商户）`, Hangzhou, China. The support address is `contact@oneshowailab.com` and must remain consistent across Contact, Terms, and Privacy. Public product copy presents AI output as guidance, requires users to verify claims and use their real experience, and directs users to follow interview-organiser rules.

The Global build produces route-specific initial HTML for `/pricing`, `/terms`, `/privacy`, `/refund-policy`, `/contact`, `/about`, and `/security`. Each entry contains its own title, description, canonical, H1, and body before JavaScript runs. Global Nginx resolves these entries before the SPA fallback. `robots.txt` references the HTTPS sitemap, which lists the canonical merchant-review URLs.

## Regional profiles

`VITE_GLOBAL_LOCALE` accepts `en-US`, `en-GB`, `en-AU`, or `en-CA`. It controls locale-sensitive presentation. All profiles map to the backend `en-US` interview-language contract until ASR and prompt providers expose a verified reason to split those contracts.

## Deferred launch dependencies

The following are intentionally not considered complete in this development change:

- independent production server, PostgreSQL, Redis, object storage, monitoring, and backups;
- Global domain, TLS, DNS, CDN, email and support configuration;
- international authentication/SMS provider and account migration policy;
- payment activation, final tax handling, checkout disclosure, and settlement;
- production AI/ASR regions, credentials, data-processing terms, capacity and latency tests;
- jurisdiction-specific legal approval, cookie/analytics consent, retention schedule, recording disclosure, and incident response;
- signed/notarised Global desktop installers and production update metadata.

Local Global development must use explicit developer endpoints. Chinese production endpoints and secrets are not a launch fallback.

## Local verification (2026-09-04 complete-experience update)

- Global Web: 29 route/copy/commerce-isolation tests passed; strict copy audit, typecheck, and production build passed with commerce disabled and provider `none`.
- Global companion: typecheck, Global renderer build, profile isolation tests, and domestic-profile regression tests passed.
- Existing Chinese Web: 349 tests, typecheck, and production build passed; no Chinese Web source was changed by this update.
- Backend: 58 targeted email/English/screenshot/production-gate tests passed. The full suite completed with 451 passed and 20 skipped; two timing-sensitive prewarm tests narrowly exceeded thresholds under full-suite load and both passed immediately in isolated reruns. No Backend implementation was changed by this complete-experience update.
- OpenSpec: strict validation passed.
- Visual browser smoke testing was not available in the current local browser runtime. Component-level route smoke tests were used instead; a real-browser visual and accessibility pass remains required before Global deployment.

## Companion parity verification (2026-09-06)

- The Global companion and Chinese companion share the same main process, renderer, capture, pairing, recovery, shortcut, and update logic at version `1.2.15`.
- The Global copy generator now requires explicit translations for 169 current Chinese source values and generates 208 composable exact/dynamic rules. Generic category-level substitutions were removed.
- `npm test -w @offersteady/desktop` regenerates the Global catalogue first and fails when new Chinese static or template copy lacks an explicit translation.
- Desktop tests passed 191/191; main and renderer typechecks, the Global renderer build, and the unchanged domestic renderer build passed.
- A real Global Electron runtime connected to `https://offersteady.com/api/v1`; device registration succeeded and the rendered interface contained English Microphone, System audio, Screen capture, pairing, and navigation copy with no visible Chinese text.
- Global packaging now rejects an API base URL that does not end at `/api/v1`, preventing a valid host with an invalid registration path from becoming a release artifact.
