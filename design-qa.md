# Homepage Content Sections Design QA

- Source visual truth: three conversation attachments showing a 1323 × 725 desktop six-card “核心功能” reference, a 1323 × 806 desktop six-card “成功案例” reference, and an 886 × 691 desktop product-metrics plus FAQ reference. The source attachments have no local filesystem paths.
- Implementation route: public homepage `/`, sections `#core-capabilities`, `#user-scenarios`, and `#product-facts`.
- Browser: Playwright Chromium 151, device scale factor 1.
- Desktop viewport: 1323 × 900 CSS pixels; full-page screenshot `/tmp/offersteady-visual-qa/home-desktop.png` (1323 × 5802 pixels).
- Mobile viewport: 390 × 844 CSS pixels; full-page screenshot `/tmp/offersteady-visual-qa/home-mobile.png` (390 × 8082 pixels).
- Focused desktop screenshots: `/tmp/offersteady-visual-qa/core-desktop.png` (1241 × 951), `/tmp/offersteady-visual-qa/scenarios-desktop.png` (1241 × 1008), `/tmp/offersteady-visual-qa/facts-faq-desktop.png` (1241 × 1120).
- Focused mobile screenshots: `/tmp/offersteady-visual-qa/core-mobile.png` (362 × 1144), `/tmp/offersteady-visual-qa/scenarios-mobile.png` (362 × 1616), `/tmp/offersteady-visual-qa/facts-faq-mobile.png` (362 × 1111).
- State: unauthenticated public homepage with a local development API and synthetic, non-persistent product state.
- Density normalization: all implementation captures use 1 CSS pixel to 1 output pixel. Source dimensions are recorded above; layout was compared by section structure and visible proportions because source files are conversation attachments rather than local image files.

**Findings**

- No actionable P0, P1, or P2 mismatch remains.
- The implementation preserves the source hierarchy: centered section introduction, desktop two-column six-card grids, four horizontally aligned metrics, and a single-column six-item FAQ.
- Intentional product adaptation: the reference light theme and unverified success claims were replaced with the existing OfferSteady dark design system, verifiable product facts, and clearly labeled synthetic scenarios, as required by the approved OpenSpec.

**Required Fidelity Surfaces**

- Fonts and typography: existing public-site font stack, heading weights, line heights, and responsive wrapping remain consistent. Desktop and 390-pixel captures show no clipping or truncation.
- Spacing and layout rhythm: desktop cards use even two-column tracks and aligned rows; mobile switches to one column for both six-card sections and two columns for metrics. Section spacing remains visually distinct without horizontal overflow.
- Colors and visual tokens: implementation reuses the established dark background, panel borders, brand mint, and restrained accent palette. Contrast is sufficient in captured desktop and mobile states.
- Image quality and asset fidelity: these sections require no raster images. Phosphor vector icons render sharply at both sizes and are decorative to assistive technology.
- Copy and content: all capability copy describes current product behavior; user scenarios are labeled synthetic; product numbers are verifiable; FAQ pricing and payment text comes from runtime state.

**Full-view Comparison Evidence**

- Desktop full-page capture shows all three new sections in the intended sequence between workflow and pricing, with the same rapid-scan hierarchy as the references.
- Mobile full-page capture shows readable content at 390 pixels with no clipped cards, hidden controls, or horizontal page overflow.

**Focused Region Comparison Evidence**

- Core capabilities: six cards render as two columns on desktop and one column on mobile, with consistent icon, title, and description alignment.
- User scenarios: six cards render as two columns on desktop and one column on mobile; every card visibly carries the “合成示例” label.
- Product facts and FAQ: four metrics render as four columns on desktop and two columns on mobile; the first FAQ is open and all six controls remain visibly operable.

**Primary Interactions Tested**

- Playwright verified six FAQ items, default-open state, mouse expansion, keyboard Enter collapse, and both viewport layouts.
- Playwright verified `scrollWidth <= clientWidth` at 1323 and 390 CSS pixels.
- Playwright captured browser console errors and uncaught page errors; both lists were empty.
- Automated component tests additionally verify dynamic welcome points, pricing rates, payment channels, legal links, prohibited claims, and semantic structure.

**Comparison History**

- Initial browser attempt exposed the expected backend-unavailable fault state because the local API was stopped.
- The local API was started with non-persistent development state and the preview origin was explicitly allowed; this was environment setup rather than a visual code fix.
- Final desktop and mobile captures contain the intended homepage. No P0/P1/P2 visual fix was required after the valid implementation capture.

**Implementation Checklist**

- [x] Desktop full-page and focused section captures.
- [x] Mobile full-page and focused section captures.
- [x] FAQ mouse and keyboard interaction checks.
- [x] Horizontal overflow checks.
- [x] Console and page error checks.

**Follow-up Polish**

- P3: consider reducing total homepage length in a future content experiment after real scroll-depth data is available.

final result: passed
