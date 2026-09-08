# OfferSteady GEO Analysis

Date: 2026-09-05  
Readiness: **22/100 — Low**  
Confidence: Moderate

## Platform view

| Platform | Readiness | Main blocker |
|---|---:|---|
| Google AI Overviews | Low | Distinct feature/guide/topic URLs do not return their own source HTML and have weak topical depth. |
| ChatGPT search | Low | OAI-SearchBot is not blocked, but GEO files are broken and public brand/entity signals are weak. |
| Perplexity | Low | Few self-contained, source-backed passages and little verified external brand discussion. |
| Bing Copilot | Low | Sitemap and indexable content surface are incomplete; Bing ownership/submission is unknown. |

## AI crawler access

`robots.txt` uses `User-agent: *`, allows `/`, and disallows only `/app/` and `/api/`. GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, and PerplexityBot are not explicitly named, but inherit the public wildcard policy. Crawler blocking is therefore not the primary issue.

## Discovery-file status

- `/llms.txt`: broken; returns homepage HTML as `text/html`.
- `/llms-full.txt`: broken; returns homepage HTML as `text/html`.
- `/public-facts.json`: broken; returns homepage HTML as `text/html`.

These files should identify the product, canonical public sources, verified feature facts, responsible-use boundary, operator, privacy/security routes, pricing status, and support contact. They must not introduce claims absent from visible HTML.

## Passage-level citability

The homepage has only 157 parsed words and no substantial answer block in the sampled source. The current H2 sections are short marketing summaries rather than self-contained explanations. Create 100–200 word sections answering questions such as:

- What is OfferSteady?
- How does OfferSteady provide real-time interview guidance?
- How does Resume and job-description grounding work?
- What does Screen Assist do?
- What data does OfferSteady process and retain?
- Which devices and interview platforms are supported?
- How should candidates use AI guidance responsibly?

Each answer should begin directly, state only verified facts, and link to a deeper canonical page.

## Authority and brand signals

Confirmed on-site positives:

- Operator information appears on Terms, About, and Contact.
- Support email is consistent.
- Privacy, Security, Terms, Pricing, and Refund pages are independently readable.

Missing or unknown signals:

- Named authors/reviewers and credentials.
- Publication and update dates on editorial content.
- Original data, case studies, demonstrations, or benchmarks.
- Official sameAs profiles.
- Verified external mentions, reviews, or community references.
- Search Console/Bing index status.

## Highest-impact changes

1. Fix server-readable feature, guide, and topic routes.
2. Fix the three GEO resources and add strict production regression checks.
3. Add truthful Organization/WebSite/SoftwareApplication/Breadcrumb/Article JSON-LD.
4. Publish answer-first, source-backed content clusters with named reviewers and update dates.
5. Build legitimate brand mentions through demos, launch profiles, technical content, and real user evidence.

## Guardrails

- Do not describe the product as cheating, undetectable, anti-detection, or a way to bypass monitoring.
- Do not fabricate user counts, success rates, latency, ratings, reviews, platform compatibility, or security certifications.
- Do not create dozens of thin role/country pages. Start with a small number of strong pages with distinct intent.
- Keep AI discovery files consistent with visible HTML and policy pages.

