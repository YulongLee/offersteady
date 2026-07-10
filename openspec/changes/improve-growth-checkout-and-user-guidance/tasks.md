## 1. Shared Contracts and Migration Boundaries

- [x] 1.1 Define official identity authorization-session, popup-result and account-binding contracts
- [x] 1.2 Define official checkout order, provider action, notification, query, refund and reconciliation contracts
- [x] 1.3 Define Windows support-readiness gates, evidence, version and revocation contracts
- [x] 1.4 Define product-asset manifest and versioned guide-content contracts
- [x] 1.5 Add backward-compatible protocol serialization and sensitive-field exclusion tests
- [ ] 1.6 Reconcile this change with the in-progress landing, identity, billing and desktop distribution specs
- [ ] 1.7 Mark manual proof ordering as legacy-only and document its read-only migration state

## 2. Conversion-Focused Public Entry

- [x] 2.1 Replace the hero with “AI 面试助手，助你更从容地冲刺 Offer” or approved equivalent
- [x] 2.2 Rewrite the supporting copy around real-time questions, personal context, screenshots and cross-device use
- [x] 2.3 Replace all public “进入产品原型” actions with “免费使用” or “立即免费体验”
- [x] 2.4 Display the 200-point new-user grant beside the primary CTA without hiding eligibility terms
- [x] 2.5 Build a direct-value section for real-time assistance, personalized answers and flexible usage rhythm
- [x] 2.6 Build a pricing-value section comparing points and 3/7/15/30-day membership from server catalog data
- [x] 2.7 Move AI-advice, truthful-experience and privacy boundaries into a discoverable secondary trust section
- [x] 2.8 Add product-evidence examples for voice, manual, screenshot and actual source labels
- [x] 2.9 Add tests preventing employment guarantees, prototype wording and client-hardcoded prices
- [ ] 2.10 Run desktop, tablet, mobile, keyboard, screen-reader, contrast and conversion-copy reviews

## 3. Verified Windows Support

- [x] 3.1 Implement server-managed Windows support-readiness records and authorized gate updates
- [x] 3.2 Require signed x64 artifact, compatible protocol and verified install/upgrade/uninstall evidence
- [x] 3.3 Require account login, binding, pairing, reconnect and microphone capture evidence
- [x] 3.4 Decide and encode whether system audio is mandatory or an explicitly approved limited capability
- [ ] 3.5 Add Windows 10/11 physical-device matrix evidence with expiry and release version
- [ ] 3.6 Compute one support status consumed by homepage, downloads and user guide
- [ ] 3.7 Show “Windows 已支持” only when the complete current-version gate passes
- [ ] 3.8 Revoke support and download visibility when release or capability evidence is withdrawn
- [ ] 3.9 Add authorization, incomplete-gate, stale-evidence, withdrawal and cross-page consistency tests
- [ ] 3.10 Complete Windows signed release, pairing, capture and physical-device verification before enabling the claim

## 4. Official WeChat Account Entry

- [ ] 4.1 Replace the development-success click handler with a server-created WeChat authorization session
- [x] 4.2 Implement a replaceable official WeChat website/official-account provider adapter
- [x] 4.3 Implement one-time state, PKCE or provider-equivalent protection, expiry and replay rejection
- [x] 4.4 Build an accessible desktop QR dialog or popup launched directly from the login click
- [ ] 4.5 Add same-page QR or same-window redirect fallback when popup creation is blocked
- [ ] 4.6 Implement waiting, scanned, authorized, expired, closed, provider-failed and callback-failed states
- [ ] 4.7 Implement allowlisted same-origin or postMessage callback completion without exposing provider tokens
- [ ] 4.8 Complete idempotent login, first registration and reauthenticated account binding
- [ ] 4.9 Route identity collisions to verified recovery without silent account merging
- [x] 4.10 Hide local prototype identity in production builds and keep it behind an explicit development flag
- [ ] 4.11 Add state replay, popup attack, callback origin, collision, expiry and provider-outage tests
- [ ] 4.12 Verify privacy disclosure, redirect domains, WeChat platform credentials and production configuration

## 5. Official WeChat Pay and Alipay Checkout

- [x] 5.1 Implement server-only provider interfaces for create, query, notify, close, refund and reconcile
- [ ] 5.2 Implement WeChat Pay Native or approved JSAPI sandbox adapter with certificate/signature verification
- [ ] 5.3 Implement Alipay computer-web or face-to-face sandbox adapter with signature verification
- [x] 5.4 Create orders from published SKU snapshots without trusting client amount, currency or entitlement
- [x] 5.5 Build checkout choice, authoritative order summary, channel, countdown and status UI
- [x] 5.6 Render short-lived order-specific WeChat QR values and official Alipay redirect or QR actions
- [x] 5.7 Remove transaction-reference, payment-screenshot and payer-identity fields from new checkout
- [x] 5.8 Remove new-order artificial “人工核验中” states and manual approval controls
- [ ] 5.9 Verify notification signature, merchant, application, order, amount, currency and paid state
- [x] 5.10 Add active server query recovery for delayed or missing provider notifications
- [x] 5.11 Activate points or membership exactly once in the same transaction as verified payment confirmation
- [x] 5.12 Keep return pages and client polling in “确认支付结果中” until server confirmation
- [ ] 5.13 Close expired payment actions and generate a fresh provider action without duplicate entitlement
- [x] 5.14 Implement authorized official refund, asynchronous result and customer-visible status
- [ ] 5.15 Preserve historical manual-proof orders as read-only while blocking new manual-order creation
- [ ] 5.16 Add provider sandbox tests for paid, cancelled, delayed, replayed, forged, wrong-amount and refund flows
- [ ] 5.17 Add end-to-end WeChat Pay and Alipay journeys through one idempotent entitlement grant

## 6. Managed Product Assets

- [x] 6.1 Create `apps/web/public/assets/brand`, `payments` and `support` directories
- [x] 6.2 Add synthetic OfferSteady logo, application icon, favicon and sharing-image fixtures
- [ ] 6.3 Add approved WeChat and Alipay channel icon assets without modifying protected brand marks
- [x] 6.4 Add synthetic customer-service and customer-group QR placeholders without production identities
- [x] 6.5 Define `assets.manifest.json` with stable ID, path/URL, purpose, alt text, dimensions, hash, version and expiry
- [x] 6.6 Implement an asset resolver with integrity, expiry, missing-resource and safe-fallback behavior
- [x] 6.7 Replace scattered brand, payment and support paths with asset IDs or controlled configuration
- [ ] 6.8 Implement authorized remote replacement and withdrawal for production support QR assets
- [x] 6.9 Ensure dynamic payment QR values bypass the static asset manifest and are never committed
- [ ] 6.10 Add manifest schema, integrity, expiry, accessibility and unauthorized-replacement tests

## 7. In-App User Guide

- [x] 7.1 Add protected `/app/guide` route and “使用说明” desktop/mobile navigation item
- [x] 7.2 Create versioned `apps/web/content/guides/zh-CN` source structure and metadata
- [x] 7.3 Write quick start, WeChat account and material-library chapters
- [x] 7.4 Write Windows/macOS install, pairing, permissions and troubleshooting chapters
- [x] 7.5 Write live assistance, speaker confirmation and screenshot-question chapters
- [x] 7.6 Write points, membership, official payment, delayed confirmation and refund chapters
- [x] 7.7 Write privacy, deletion, FAQ and customer-service escalation chapters
- [x] 7.8 Implement safe Markdown/structured-content rendering with script and unsafe-link rejection
- [x] 7.9 Build responsive contents navigation, search, stable anchors and previous/next controls
- [ ] 7.10 Link library, preparation, devices, live workspace and billing pages to contextual guide anchors
- [x] 7.11 Add configured customer-service and customer-group contact cards with expired-asset fallback
- [ ] 7.12 Add route protection, search, anchor compatibility, unsafe-content and accessibility tests

## 8. Security, Operations and Release Verification

- [x] 8.1 Store identity, payment and signing secrets only in controlled server/release environments
- [ ] 8.2 Redact provider codes, tokens, payment identities, dynamic QR values and callback payloads from logs
- [ ] 8.3 Add immutable audits for support readiness, asset changes, payment confirmation, refund and entitlement activation
- [ ] 8.4 Add rate limits and abuse protection for login sessions, payment creation, status polling and QR refresh
- [ ] 8.5 Verify CSP, callback origins, popup messaging, redirect allowlists and asset-host restrictions
- [ ] 8.6 Verify existing manual orders remain supportable without exposing proof data in the new checkout
- [ ] 8.7 Run the landing → free use → official WeChat login → guide → checkout journey
- [ ] 8.8 Run the supported Windows download → install → bind → capture → manual fallback journey
- [x] 8.9 Run full typecheck, unit, integration, production build and OpenSpec strict validation
- [ ] 8.10 Define launch dashboards for CTA conversion, login completion, payment success, delayed confirmation and guide search gaps
