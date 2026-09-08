## Context

The Global site already generates independently crawlable public HTML from a shared catalogue and serves it through an inner Nginx container behind host Nginx. The September 5 production audit found that this search surface is healthy, but it also found a campaign-attribution defect in trailing-slash canonicalisation, a dead-end Download page, thin feature and hub content, several weak metadata fields, difficult homepage copy, and a 772 KB social image. The authenticated application and all core interview services are healthy and must remain isolated from this public-site change.

The product is still pre-payment and does not yet publish approved Global desktop installers, customer proof, official social accounts, analytics ownership, or CDN configuration. The implementation therefore has to improve discoverability and conversion using only verified product facts and existing public routes.

## Goals / Non-Goals

**Goals:**

- Preserve campaign query parameters while canonicalising public URLs.
- Give visitors on `/download` a truthful next action before installers are approved.
- Improve metadata, content usefulness, readability, and social-image transfer size.
- Keep static HTML, hydrated React content, sitemap, GEO files, and public facts consistent.
- Extend automated release gates so the observed defects cannot silently return.
- Deploy only the Global Web image after confirming there is no active Global interview traffic.

**Non-Goals:**

- No changes to the Chinese product or server.
- No changes to authentication semantics, interview or written-exam behavior, Companion capture, ASR, RAG, AI prompts/models, Backend APIs, databases, Redis, Admin, or payment activation.
- No invented download links, installer compatibility claims, users, testimonials, reviews, authors, social profiles, integrations, rankings, outcomes, or performance claims.
- No analytics, cookies, consent mechanism, CDN, DNS, Search Console, or Bing configuration.
- No public international partner program or user manual.

## Decisions

### Preserve the query string at the existing canonical redirect

The inner Nginx trailing-slash redirect will append `$is_args$args` to the canonical non-slash URL. This fixes UTM loss at the earliest affected layer without changing the route catalogue, application router, cookies, or API behavior.

Redirecting in React was rejected because crawlers and attribution systems can act before JavaScript executes. Removing canonicalisation was rejected because it would create duplicate public URLs.

### Add a catalogue-driven public action model

The public catalogue will support optional actions. `/download` will use this model to send a visitor to the existing `/login` Start Free path and explain that verified installers are presented inside the signed-in preparation flow. Both generated HTML and the React view will render the same action.

Publishing guessed installer URLs or copying a domestic artifact was rejected because the Global release channel is not yet approved. Hard-coding `/download` behavior in the component was rejected because it would recreate drift between static and hydrated output.

### Improve content in the existing verified route set

The implementation will deepen the four feature pages, guides, interview-question hub, and Download page with practical explanations, limitations, setup or review checklists, and responsible-use guidance. Copy will use shorter sentences and scannable sections, and metadata will stay unique and within the verifier's quality ranges.

Generating additional keyword pages was rejected because the site does not yet have enough reviewed source material to support a broader programme without thin or repetitive pages. Fabricated authority signals were rejected outright.

### Optimise the approved share card in place

The existing 1200 by 630 share image will be losslessly or visually safely recompressed while retaining the same public URL and dimensions. A build assertion will cap its size so future exports do not restore the oversized payload.

Changing the visual brand or adding new claims to the image was rejected because this task is performance work, not a new design approval.

### Gate public changes without widening production scope

Source and build tests will verify action parity, metadata quality, minimum useful content, query-preserving redirects, image dimensions and size, prohibited copy, route isolation, and the pre-payment boundary. Deployment will rebuild and restart only the Global Web service, then verify raw production HTML and redirects with `curl`.

A full Compose restart was rejected because Backend, database, Redis, analytics, and Admin are outside the change and should not incur availability risk.

## Risks / Trade-offs

- [More public copy can weaken scanability] → Use short sections, descriptive headings, compact paragraphs, and retain one primary action.
- [Static and React output can diverge] → Keep content and actions in the catalogue and verify both source-generated HTML and component rendering.
- [A redirect syntax mistake can lose or duplicate query parameters] → Exercise the exact Nginx configuration in a container smoke test and verify production with raw `curl` before completion.
- [Image compression can reduce legibility] → Preserve 1200 by 630 dimensions and inspect the optimised artifact before release.
- [The Download CTA may be mistaken for a direct installer] → Label it Start Free and explicitly state that verified release options appear in the signed-in preparation flow.
- [Content assertions can encourage filler] → Set a moderate route-class threshold and review for verified, non-repetitive, user-useful content rather than keyword density.

## Migration Plan

1. Record the current Global Web image, release marker, container health, Nginx configuration, and active-session state.
2. Generate the public documents and run Global type, unit, copy, metadata, route, asset, and production-build tests locally.
3. Run Chinese Web regression tests to prove the separate application remains untouched.
4. Create a versioned overseas release and candidate Global Web image without restarting any production service.
5. Smoke-test the candidate on a loopback-only port, including query preservation and application-route isolation.
6. If no Global interview is active, replace only the Global Web container and verify every public route, `/download`, UTM redirects, login noindex behavior, unknown 404 behavior, health, and recent logs.
7. Roll back to the recorded Web image and configuration if any public or existing application contract fails.

## Open Questions

- CDN and target-market field performance require DNS ownership and regional measurements; they remain a separate infrastructure decision.
- Search Console, Bing Webmaster Tools, analytics, and conversion events require account access and a consent decision.
- Product screenshots, customer proof, named reviewers, official social profiles, a domain-matching support address, and signed Global installers require owner-provided assets or approvals and are intentionally absent.
