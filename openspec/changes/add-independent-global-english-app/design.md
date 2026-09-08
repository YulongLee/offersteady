## Context

The current `apps/web` application is the validated Chinese end-user product, `apps/admin` is the Chinese operator console, `apps/backend` owns the API and AI orchestration, and `apps/desktop` owns the companion. English interview prompts and backend language enforcement already exist, but the complete product shell remains Chinese and current release/deployment assets target the Chinese product.

The operator wants to develop the United States, United Kingdom, Australia, and Canada edition now, then supply a separate server, domain, and payment method before launch. Protecting the current Chinese production path is the dominant constraint.

## Goals / Non-Goals

**Goals:**

- Deliver independently runnable and buildable Global web and companion applications.
- Preserve current end-user feature coverage while making the entire customer experience English.
- Reuse stable API contracts, realtime behavior, and AI orchestration rather than fork backend business logic prematurely.
- Default all Global sessions to the existing English interview path.
- Provide regional profiles for US, UK, Australia, and Canada.
- Prove through automated checks that the Chinese web, companion, and admin defaults remain intact.

**Non-Goals:**

- Deploying to production or changing current Chinese infrastructure.
- Selecting or activating international authentication, payment, email, SMS, AI, storage, or hosting providers.
- Providing final jurisdiction-specific legal advice or approved legal copy.
- Redesigning the Global visual system in this migration; initial layout and behavior remain aligned with the validated product.
- Translating the administration application.

## Decisions

### 1. Separate app entry and artifact, shared stable contracts

Create `apps/web-global` as a separately named Vite workspace with its own HTML metadata, public runtime configuration, tests, and `dist` output. For this first isolated development version, it starts from a source snapshot of the validated customer application while continuing to consume the same protocol/config packages and backend API contracts. Global-specific presentation and defaults remain inside that workspace, so its build cannot replace the Chinese artifact. Stable runtime capabilities should be extracted into shared packages incrementally when both editions need the same future fix.

Alternative considered: add a runtime language switch directly to `apps/web`. Rejected because a single deployable artifact and broad conditional rendering would increase regression and configuration-leak risk for the Chinese production application.

The snapshot is not intended to justify permanent divergence. Every cross-edition realtime or security change must be applied and tested in both applications until that module is extracted into a shared package.

### 2. Product edition is build-time, locale is runtime-safe public configuration

The Global package fixes the product edition to `global`; it accepts only supported public locale values (`en-US`, `en-GB`, `en-AU`, `en-CA`) and defaults safely to `en-US`. Secrets and provider credentials remain backend-only.

Alternative considered: infer edition from hostname. Rejected because local development, previews, proxies, and future custom domains make hostname inference fragile and capable of exposing the wrong product shell.

### 3. One English AI contract for all four initial markets

The backend currently supports `zh-CN` and `en-US` as interview-language contracts. All four Global presentation locales map to the backend `en-US` contract for ASR and answer generation in this release. Locale changes spelling, formatting, and product metadata but does not create unsupported backend enum values.

Alternative considered: immediately add `en-GB`, `en-AU`, and `en-CA` backend language variants. Rejected because it would expand ASR/prompt behavior without evidence that the provider requires or benefits from those enum values.

### 4. English text is generated before render and testable

High-visibility Global pages and legal/help content use explicit English source. Remaining inherited static product strings are collected at build time into a deterministic English catalogue and translated by the Global-only JSX runtime before React creates the element. Arbitrary user content is not translated. Dynamic validation and backend failures pass through a Global error-message boundary so expected domain errors have English equivalents while unknown technical details remain safely generic.

Alternative considered: a MutationObserver that replaces Chinese DOM text. Rejected because it causes visible language flashes, misses attributes and generated exports, and is unsuitable for accessibility or commercial QA. The implemented path performs no DOM mutation and audits the generated values before build.

### 5. Preserve admin and Chinese defaults

`apps/admin` is outside the implementation edit scope except for read-only regression verification. Chinese `apps/web` and the default desktop build remain the source of their existing production artifacts. Workspace commands gain additive Global targets rather than changing existing command meanings.

### 6. Desktop uses an additive Global build profile

Companion runtime behavior remains shared. Product name, locale strings, website URL, update URL/channel, application identifier, and output filename are selected by an explicit Global build profile. No current signing identity, Chinese version metadata, or release file is overwritten.

The Global copy generator inventories both static strings and the literal fragments of dynamic status messages. Every inventory entry requires an explicit English mapping; category-level fallback copy is prohibited. The normal desktop test command regenerates this catalogue, so a Chinese companion change cannot pass verification while its Global presentation is stale. Dynamic runtime messages compose the same approved fragments, while an unknown provider-supplied Chinese failure is replaced by one safe English recovery message rather than exposed untranslated.

The packaged Global main process identifies its edition from the Global-only runtime configuration resource embedded in the artifact. Runtime application display names are not a reliable edition boundary during Electron's early startup and SHALL NOT be the deciding signal for endpoint or user-data selection. Development builds may use the explicit edition environment variable; Chinese packages do not contain the Global resource.

### 7. Deployment configuration remains intentionally incomplete

Provide example/contract files for Global public endpoints, but do not insert placeholder production credentials or silently reuse Chinese production endpoints as a launch configuration. Local tests may target a developer backend through explicit environment variables.

## Risks / Trade-offs

- [Shared implementation changes could regress Chinese behavior] → keep Chinese defaults unchanged, use additive entry points, and run the existing Chinese web/backend/desktop regression suites before completion.
- [“All features” contains substantial static and dynamic copy] → inventory routes and customer-facing states, fail the Global companion build on missing exact or template translations, add a no-Han-character audit for generated Global values, and test representative states for every journey.
- [Backend may return Chinese domain messages] → translate known error codes at the Global boundary and use a generic English fallback without changing backend responses used by Chinese clients.
- [Current authentication or payment providers may not work internationally] → preserve the interfaces for functional migration, clearly mark production activation deferred, and avoid claiming launch readiness until providers are supplied and verified.
- [Regional vocabulary can be over-specialised] → localise only deterministic formatting and approved terminology; keep interview answer style controlled by user/job context rather than nationality stereotypes.
- [Desktop profile can accidentally target Chinese services] → require explicit Global endpoint variables and validate release metadata before building a Global artifact.

## Migration Plan

1. Add and validate the independent Global application and configuration contract without touching production deployment files.
2. Add English feature coverage and AI-language regression tests.
3. Add the independent companion profile and build validation.
4. Run Global plus existing Chinese/admin/backend/desktop tests and builds.
5. When the operator later supplies infrastructure, create a separate deployment change for Global server, storage, database, cache, domain, authentication, payment, monitoring, and secrets.
6. Deploy to an isolated Global environment and execute smoke, privacy, billing, realtime, accent, weak-network, and rollback tests before traffic.

Rollback for the future production change will operate on Global artifacts only. The Chinese deployment is not part of that release unit.

## Open Questions

- Which international authentication provider and account identifier will replace or supplement the current China-oriented login methods?
- Which product name, legal entity, support address, retention schedule, and final privacy/terms text will be approved for launch?
- Which server regions and AI/ASR providers will meet latency, data-transfer, and commercial requirements for the four markets?
- Which payment provider, currencies, prices, tax handling, and refund policy will be configured?
