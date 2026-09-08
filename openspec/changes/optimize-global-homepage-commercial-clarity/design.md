## Context

Production baseline global-review-20260907.1. English homepage primary conversion is free account creation because live payments are unavailable. Audience: job seekers evaluating interview assistance; traffic mix and actual conversion/volume unknown. Current UI repeats preparation/live/review across workflow, capabilities and responsible-assistance blocks, interleaves two large videos, and delays pricing until after the full comparison.

## Goals / Non-Goals

Goals: concise benefit-led English, clear free action/downloads, earlier pricing, fewer repeated blocks, accessible FAQ/comparison, static parity, current dark/mint design.

Non-goals: deployment, changing plans or legal policies, new testimonials/metrics, competitor research/re-pricing, analytics integration, dependencies, backend/auth/AI/capture changes.

## Decisions

- Retain App's LandingPage boundary; move only static homepage text/media definitions into a JSON catalogue shared with the static generator. Avoid a broad application refactor or new UI framework.
- Order: hero → four feature benefits → existing feedback → canonical pricing → three setup steps and two compact videos → optional full comparison → FAQ → final CTA → existing legal footer. Compared with simply deleting disclosures, concise notes and policy links preserve transparency.
- Hero has one short description, Start free and an in-page tour link, current download component and one-line guidance note after actions. No manufactured urgency, performance numbers, guaranteed result or anonymous authority claim.
- Preserve plan cards' real features and billing; state confirmed-payment access start once beneath the cards and link to full terms. Pricing remains canonical from public-review-pages.json, never a duplicate price list.
- Native details/summary for FAQ and comparison: keyboard accessible and no new JavaScript state/network. Keep dated comparison data and limitations intact; do not represent a new market review.
- Preserve all 20 feedback entries and provenance note. Preserve both video assets, controls/muted/playsInline/preload=metadata and no autoplay.
- Align no-JavaScript homepage H1, benefits, media, plan data, FAQs, support/operator with rendered UI. Do not change independent legal/pricing page policies.

## Risks / Trade-offs

- Conversion gain is unmeasured → report verified layout/copy changes, propose future measurement without claiming percentages.
- More concise copy can imply free includes paid features → explicit Free limits in pricing/FAQ and full-price link.
- Collapsed comparison is less immediately visible → prominent descriptive summary, full table still accessible and unchanged when expanded.
- Existing 900px navigation overflow → fix only public navigation wrapping if observed; verify 1440/900/390/320px.
- Mobile two-video stack remains → compact copy, existing metadata-only loading and no autoplay; no new heavy media.

## Migration Plan

Local implementation and acceptance only. Deployment requires a subsequent request and the existing overseas-only, idle-gated Web release process.
