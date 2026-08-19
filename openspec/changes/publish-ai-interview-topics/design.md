## Context

The public site now has product pages, guide hubs, and four foundational interview guides. The next approved cluster targets AI engineering candidates and must distinguish model fundamentals, retrieval systems, and agent orchestration rather than duplicating one generic AI article.

## Goals / Non-Goals

**Goals:**

- Answer three distinct AI interview intents with standalone, server-rendered Chinese articles.
- Ground technical claims in original papers, standards, or official framework documentation.
- Teach candidates to explain definitions, components, trade-offs, failure diagnosis, evaluation, and production boundaries.

**Non-Goals:**

- No live question bank, answer memorization tool, model comparison, benchmark leaderboard, course, CMS, or authenticated product change.
- No claim that cited organizations endorse or integrate with 面试稳.
- No FAQPage schema; visible FAQs remain Article content.

## Decisions

1. **One system boundary per page.** LLM covers model behavior and inference concepts; RAG covers retrieval-grounded generation; Agent covers stateful tool-using workflows.
2. **Use primary technical sources.** Transformer, RAG, RAGAS, Lost in the Middle, ReAct, NIST, and official orchestration docs support definitions and limitations.
3. **Use interview-ready structures, not canned answers.** Each question includes what to explain and what trade-off to surface; candidates must adapt it to real work.
4. **Keep static delivery.** Pages use the current zero-runtime-JavaScript public template, 20 KB per article budget, and shared CSS.
5. **Release atomically.** All three topics, hub links, routes, CSP hashes, sitemap, GEO files, and verification move together.

## Risks / Trade-offs

- **[Risk] Fast-moving terminology becomes stale.** → Prefer stable architectural concepts, show review dates, and avoid provider/version claims.
- **[Risk] Keyword pages become shallow lists.** → Require system diagrams in prose, diagnostics, evaluation tables, and follow-up questions.
- **[Risk] Content suggests there is one correct architecture.** → State workload assumptions and compare trade-offs rather than prescribing a universal stack.
- **[Risk] AI-generated content creates false authority.** → Use organization-level review, visible source boundaries, and no invented experience or metrics.

## Migration Plan

Publish the three pages with their discovery and release controls, run the 27-page suite and production build, deploy Web only, and verify online canonical/noindex/404/health behavior. Roll back the Web image if any check regresses.

## Open Questions

None. Java backend, frontend, and algorithm topics remain the next content package.
