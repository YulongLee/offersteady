## Context

`apps/web-global` was created as an isolated build of the Chinese customer application. Its build step currently rewrites Chinese JSX literals by consulting a small exact dictionary and then substituting long category-level sentences for unknown strings. That fallback makes the build appear translated while losing the meaning of labels, headings, counters, empty states, and actions; the longer sentences also break layouts. The Global billing component additionally inherits domestic checkout and referral concerns that are not part of the intended international product.

The Chinese product and admin are stable production surfaces and must remain unchanged. Global is independently built and deployed at `offersteady.com`; its current production release is the rollback baseline. No additional interview audio, transcript, screenshot, or profile data is introduced by this work.

## Goals / Non-Goals

**Goals:**

- Make every supported Global customer route use explicit, concise, context-correct English product copy.
- Prevent future generic fallback translations and mixed-language product chrome at build time.
- Make existing Global flows readable and usable at desktop, tablet, and mobile widths without redesigning the product identity.
- Remove referral behavior from Global and isolate Global billing from domestic payment providers.
- Define a replaceable server-side commerce boundary suitable for a later Creem implementation.
- Keep deployment isolated and safely reversible.

**Non-Goals:**

- Changing the Chinese Web, Chinese admin, domestic referral, or domestic payment behavior.
- Activating Creem checkout before product IDs, currencies/prices, API credentials, webhook secret, tax/refund policy, and legal copy are approved.
- Translating administrator tooling, user-entered material, interview transcripts, or server-originated source documents.
- Replacing the existing design system or changing interview/audio/screenshot processing.

## Decisions

### Use an explicit static product-copy catalogue

The build-time extractor will enumerate product-authored Han-containing literals and require each one to have an explicit English mapping. Missing mappings fail the Global copy audit/build with source location. Runtime values not present in the catalogue remain unchanged so user content is never silently translated or corrupted.

This is preferred over the current category fallback because it preserves context and makes omissions visible. Runtime machine translation was rejected because it adds latency, cost, nondeterminism, privacy exposure, and a new production dependency. A fully independent rewrite of all Global pages was rejected because it would duplicate working interaction logic and increase drift.

### Correct pages route by route using the existing design system

The implementation will keep the current typography, dark/green palette, icon library, spacing tokens, and component patterns. Each route will receive concise English labels and targeted responsive rules, with critical states covered by tests. Shared components will be fixed once when their behavior is genuinely shared; route-specific copy will stay route-specific.

This is preferred over global font shrinking or overflow clipping, which hides the symptom and degrades readability.

### Separate Global billing presentation from domestic commerce

Global will use a dedicated billing surface that reads existing balance, entitlement, usage rules, and ledger APIs but does not mount referral effects or domestic checkout/polling/QR logic. The Global `/invite/:code` route will no longer activate referrals; legacy links will safely redirect to the normal public entry flow.

This is preferred over feature-hiding with CSS because hidden domestic components can still execute API requests. Modifying shared backend referral behavior was rejected because the domestic product still needs it.

### Prepare, but do not simulate, the Creem provider boundary

Future Global checkout will be initiated by the backend, which will translate a stable internal purchase request into a Creem checkout session. Browser code will receive only a redirect URL and public state. Payment and entitlement crediting will occur only after a verified, idempotent webhook; a success-page redirect will never be the source of truth. Provider identifiers will be stored alongside internal order identifiers so Creem can later be replaced without rewriting the ledger.

Until the required live configuration is present, purchase actions remain absent or explicitly unavailable. API keys and webhook secrets remain server-side. Reusing domestic payment APIs or embedding Creem secrets in Vite configuration was rejected.

### Verify isolation before deployment

Global route/copy/responsive tests, typecheck, production build, and OpenSpec validation must pass. Relevant Chinese Web regression tests/build must also pass before deployment. Only Global services may restart; their health and the Chinese production health are checked after deployment. Rollback repoints Global to the recorded baseline release.

## Risks / Trade-offs

- [Large copy catalogue can become stale] → Make extraction and explicit mapping completeness part of every Global build.
- [Automated no-Han checks can reject legitimate user content] → Audit only product-authored literals and tagged UI chrome; preserve runtime content.
- [Removing the referral route breaks old shared links] → Redirect legacy Global invite URLs to the public entry flow without applying a code.
- [Splitting Global billing duplicates some presentation logic] → Share typed read-only account models, but keep provider-specific UI and effects isolated.
- [Responsive regressions are hard to prove without a browser] → Add deterministic component/route tests now and require a real-browser visual pass at fixed viewports before release approval.
- [Creem semantics may change before integration] → Keep the provider adapter behind an internal commerce contract and validate against official test mode during the future payment change.

## Migration Plan

1. Record the current Global production image/release as the rollback target.
2. Add strict copy extraction and complete route-specific English mappings.
3. Remove Global referral route/UI/effects and introduce the Global-only billing surface.
4. Fix and test feature pages by route and viewport class.
5. Run Global and domestic regression verification without changing production.
6. After explicit approval, deploy only Global services and run health/route smoke checks.
7. If any critical Global flow regresses, restore the recorded Global release; no domestic rollback is required.

## Open Questions

- Creem product IDs, price/currency matrix, test/live credentials, webhook secret, refund policy, and customer-portal policy will be supplied and approved in a separate change.
- Final legal review is still required for Global Terms, Privacy, payment disclosures, and regional consumer rules.

