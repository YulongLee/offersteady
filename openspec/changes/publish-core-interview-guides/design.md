## Context

The public content architecture now separates product features, interview topics, editorial guides, and the product manual. Six guide pages exist, but most address device setup; the preparation side needs a first coherent cluster that is useful without requiring the product.

## Goals / Non-Goals

**Goals:**

- Answer four foundational interview intents with complete, scannable Chinese guides.
- Use a consistent evidence model: direct answer, framework, examples clearly labelled as templates, common mistakes, FAQ, sources, reviewer and dates.
- Connect informational visitors to relevant preparation and product pages without turning articles into sales copy.

**Non-Goals:**

- No company-specific question bank, guaranteed answer, fake candidate story, scraped content, user-generated content, or automated publishing pipeline.
- No authenticated product, API, model, prompt, data, or pricing changes.
- No FAQPage schema; visible FAQs remain normal article content.

## Decisions

1. **Hand-author four static Article pages.** This preserves the existing server-rendered pattern and allows editorial review. A CMS is unnecessary for the first cluster.
2. **Treat examples as fill-in frameworks, not model answers.** Templates must explicitly require users to replace placeholders with verifiable personal facts.
3. **Use organization-level authorship.** “面试稳产品与支持团队” is the maintained public reviewer; no individual expertise or first-hand result will be invented.
4. **Cite stable career guidance sources sparingly.** Sources support structured interviewing and preparation concepts; product-specific claims remain tied to public product pages.
5. **Allow a larger article HTML budget than directory pages.** Deep guides may use up to 20 KB while keeping zero runtime JavaScript and the existing CSS budget.

## Risks / Trade-offs

- **[Risk] Generic articles add little search value.** → Include concrete worksheets, answer checks, follow-up questions and failure patterns.
- **[Risk] Templates encourage fabricated stories.** → Put truthfulness warnings beside every example and never provide invented achievements as facts.
- **[Risk] Four pages overlap.** → Assign one primary intent per page and use links instead of duplicating long sections.
- **[Risk] Content becomes stale.** → Include reviewed/modified dates and source-boundary notes in HTML and Article data.

## Migration Plan

Publish the four pages, update discovery/routing atomically, run the 24-page release suite and production build, deploy only the Web image, then verify all canonical routes. Roll back the Web image if routing or rendering regresses.

## Open Questions

None. Technical topic pages remain a later change.
