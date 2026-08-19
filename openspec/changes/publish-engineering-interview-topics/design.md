## Context

The content architecture deliberately exposes only completed pages. This package turns the three remaining category summaries into useful engineering preparation guides while preserving the existing static, zero-runtime-JavaScript delivery pattern.

## Goals / Non-Goals

**Goals:**

- Give each engineering direction a distinct system boundary and interview-ready framework.
- Connect fundamentals to diagnosis, trade-offs, testing, and truthful project evidence.
- Cite official language/platform documentation or university course material for stable concepts.

**Non-Goals:**

- No company-specific bank, copied LeetCode solution catalog, framework version matrix, live playground, CMS, or authenticated feature change.
- No claim that referenced organizations endorse 面试稳.

## Decisions

1. **Java backend is a system page, not a Spring cheat sheet.** It links language concurrency and JVM concepts to database, cache, messaging, resilience, and observability decisions.
2. **Frontend starts from browser behavior and user outcomes.** JavaScript scheduling, rendering, network, accessibility, state, and performance are connected rather than listed by framework.
3. **Algorithms emphasize reasoning.** Clarification, invariant, complexity, boundary cases, implementation, and testing matter more than memorizing final code.
4. **Use primary, stable sources.** Oracle/JLS, MDN/W3C, and MIT OpenCourseWare support factual foundations; implementation advice is explicitly contextual.
5. **Use existing release controls.** Each article has a 20 KB source budget and the entire public surface advances atomically from 27 to 30 pages.

## Risks / Trade-offs

- **[Risk] Breadth produces shallow content.** → Use question maps, diagnostic tables, and answer frameworks rather than exhaustive term lists.
- **[Risk] Version-specific advice ages quickly.** → Link to current official documentation and focus on stable behavior; label version assumptions.
- **[Risk] Candidates copy answers without understanding.** → Provide reasoning checks and require real project evidence instead of canned claims.

## Migration Plan

Publish all three pages with hub/discovery/routing checks, run the 30-page suite and full Web regression, deploy Web only, then verify online routes, canonical metadata, noindex/404 controls, and service health.

## Open Questions

None. A future editorial calendar can expand each pillar only after search data is available.
