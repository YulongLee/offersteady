## Why

The Global public site is now technically crawlable, but high-intent visitors still encounter a dead-end Download page, campaign attribution can be lost during URL normalisation, and several public pages remain too shallow or hard to scan for competitive search and AI citation. These gaps should be corrected while the international product is still pre-payment and before paid acquisition begins.

## What Changes

- Preserve query parameters, including UTM attribution, when canonicalising trailing-slash public URLs.
- Give the public Download page a clear Start Free/sign-in path without publishing unverified installer artifacts.
- Improve short titles and descriptions while preserving unique canonicals and current product promises.
- Expand and simplify verified English feature, guide, interview-topic, and download content without adding unsupported claims, testimonials, identities, integrations, or outcomes.
- Reduce the social share image payload while retaining its approved 1200×630 presentation.
- Extend build and production regression checks for attribution, public conversion actions, content depth, metadata, asset size, and core-route isolation.

## Capabilities

### New Capabilities

- `global-public-growth-conversion`: Covers campaign-safe public routing, actionable public conversion paths, verified search-content depth, metadata quality, and public-asset performance for the Global site.

### Modified Capabilities

- None. The preceding public-search change has not been archived into the main specs; this change preserves its behavior and adds a separately testable growth/conversion contract.

## Impact

- Affected: `apps/web-global` public catalogue/generator, public route rendering/navigation, Global inner Nginx routing, public-search regression scripts, Global Web image, and overseas host ingress only where required.
- Unaffected: Chinese production, Global login semantics, authenticated interview and written-exam behavior, Companion, ASR, RAG, AI prompts/models, APIs, Backend, database, Redis, Admin, analytics, and payment activation.
- No new runtime dependency, API, database table, cookie, analytics provider, installer binary, or payment provider is introduced.
