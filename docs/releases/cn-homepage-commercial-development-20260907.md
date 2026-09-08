# Chinese homepage commercial clarity — development

Status: implemented locally, **not deployed**. No production server was changed during this task.

## Baseline and location

Implementation and OpenSpec live in `/private/tmp/offersteady-cn-release-20260907.DTlvCc`, the documented domestic release worktree. The primary workspace's `apps/web/src/App.tsx` lacks deployed partner features and was deliberately not overwritten or used as a release source.

Previous domestic release recorded in this project: `cn-usage-film-partner-nav-20260907.1`. Before any future deployment, compare again with actual production; this development task did not read or change domestic server state. Before-edit snapshots are in `/private/tmp/cn-home-commercial-before`.

Change: `openspec/changes/optimize-cn-homepage-commercial-clarity` in that worktree. All five implementation/check/handoff tasks complete; acceptance exceptions below are not waived.

## Strategy and copy

Audience: Chinese job seekers. Primary action: existing free-use/SMS-login journey. Traffic, current conversion rate and conversion uplift are unknown. The page-cro and write-landing skills guided hierarchy and concise copy; OpenSpec proposal/apply skills managed scope and acceptance.

Headline: **AI 面试助手，让你的经历更好表达。**

Description: 跟上面试问题，结合你的简历与目标岗位，整理更贴合自己的回答思路。

Order: hero → four benefit cards → live domestic pricing → three setup steps and both existing videos → optional platform/role details → existing six FAQs → final action → enabled partner promotion → existing footer.

Four benefits: 跟上每一个问题 / 回答更贴合你的经历 / 截图题，也有思路 / 让下一场准备更充分。

- Retained header and desktop/mobile workbench partner navigation, activity-enable check and protected dashboard. No enrollment or settlement changes.
- Preserved contact configuration, WeChat, email, Douyin/Xiaohongshu, user guide, legal links and both filing numbers.
- Pricing reads existing published valid paid passes, rates and knowledge allowances. Missing/unpublished/invalid items never become a fabricated zero-price pass. No international plans copied, no checkout writes or new API calls.
- Removed unsubstantiated hardcoded 10W+/98%/1W+/100+ metrics; no replacement testimonials, guarantees or performance claims.
- Existing video sources/posters unchanged, native controls/muted/playsinline/preload metadata/no autoplay.
- Static homepage core copy, setup, FAQs, partner navigation and filing links updated. Static pricing deliberately refers to live billing rather than bake test data into HTML. Existing title, canonical, metadata, Baidu verification and JSON-LD preserved.

## Verification

- Full Web suite: **366/366 tests passed**. Includes existing partner tests and seven new homepage cases covering real configuration, missing/unpublished/invalid prices, native media, section order and static copy.
- TypeScript and production-mode build passed. Main entry JS: 429,278 bytes (gzip approximately 129.34 kB).
- Browser checks at 1440/900/390/320 px passed, including expanded optional details, no page overflow, four benefits, five synthetic catalogue cards, partner promotion and both video properties. Corrected narrow-screen platform name overflow and hero note specificity.
- Local build HTTP `/`, `/guide.html`, `/robots.txt`, `/sitemap.xml`: 200. Direct homepage HTML contains one expected H1, benefits/setup/FAQ/support/filings/canonical, without executing JavaScript.
- OpenSpec strict validation passed.

### Acceptance exceptions / existing technical debt

Two broader SEO checks remain failing. Do not report all checks green or bypass their thresholds:

1. `test:seo-p0` expects an explicit `www.mianshiwen.cn` → apex 308 redirect inside `infra/nginx/default.conf`; it is absent in the existing worktree configuration and its HEAD baseline. That file was not modified by this task. Actual host-level production routing was not checked here.
2. `test:seo-build` sets a 410,000-byte entry-JS budget. New build is 429,278 bytes. A controlled build substituting only the saved pre-edit App.tsx with the same dependencies/settings yielded 441,072 bytes, showing this limit was exceeded before the change. Do not infer user-perceived speed improvement from this byte comparison. No core route/bundle architecture was changed merely to pass the budget.

Tests emitted existing localstorage-file runtime warnings. No dependencies were upgraded. No real user, audio, interview, payment, email or production load testing was performed.

## Previews

These use synthetic catalogue/contact state, not a production-price confirmation. Runtime pricing remains server-driven.

- [Desktop homepage](../../design/previews/cn-home-commercial/hero-1440.png)
- [Mobile homepage](../../design/previews/cn-home-commercial/hero-390.png)
- [Desktop pricing](../../design/previews/cn-home-commercial/pricing-1440.png)
- [Mobile partner entry](../../design/previews/cn-home-commercial/partner-390.png)
- [Measurements](../../design/previews/cn-home-commercial/measurements.json)

## Deployment handoff

Changed production files: `apps/web/src/App.tsx`, new `apps/web/src/homepage-commercial.css`, and `apps/web/index.html`. Tests: `App.test.tsx`, `App.product-experience.test.tsx`, new `homepage-commercial.test.tsx`. Local synthetic preview: `design-preview.html`, `src/test/homepage-design-preview.tsx`; these are excluded from production Rollup entries.

Do not deploy the primary workspace or an entire dirty worktree. A future authorized release must compare the scoped files against current domestic production, preserve all intervening user changes, retain rollback, recheck idle interviews/transports/answer tasks, build the domestic Web and verify real HTTP/browser behavior. Existing SEO checks above require a separate decision before representing complete commercial/SEO readiness. International services remain untouched.
