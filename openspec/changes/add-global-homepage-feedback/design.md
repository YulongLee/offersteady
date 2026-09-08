## Context

The Global homepage uses dark panels, mint accents and concise typography. The user approved implementation and supplied a 20-entry Chinese feedback list and poster, asserting authenticity. Only feedback text is used; poster identities/photos/likes are excluded. Authenticity has not been independently verified and must not be claimed as verified.

## Goals / Non-Goals

Goals: English-only text; faithful positive and critical feedback; anonymous attribution; responsive accessible carousel; no new dependencies or API traffic.

Non-goals: fabricating testimonials or social proof, claiming these describe Global prices, changing pricing or product features to match suggestions, changing China or authenticated workflows.

## Decisions

- Store 20 anonymous translations in a local JSON catalogue, shared by client and static HTML generation. Generic topic labels are editorial navigation, not invented identities.
- Render three cards on desktop, two on tablet, one on mobile. Advance one entry every 10 seconds while visible; previous/next wrap across all 20 entries. Touch swipes provide manual navigation.
- Pause on hover, keyboard focus, explicit pause, hidden document or offscreen section. Reduced-motion preference disables automatic rotation by default. Focus/manual navigation require explicit Play to resume.
- Keep full quotes, including requests for improvements. Add an English note: translated submissions; experiences and plans may differ by edition. No review/aggregate-rating schema or invented numerical endorsement.
- Use scoped CSS, no avatars, photos, libraries or backend work. Static homepage offers the same entries in an expandable list, without JavaScript-only controls.

## Risks / Trade-offs

- Owner-supplied attribution is not independent verification: do not add verified badges or claim verification; preserve provenance in development notes.
- Regional experiences differ: retain translation/edition note and do not introduce dollar prices or product claims into quotes.
- Motion/readability: 10-second interval, full visible copy, pause on interaction, reduced-motion support and manual access to every entry.

## Open Questions

None. The follow-up request explicitly approves Global production deployment. Overlay only the scoped homepage files on the verified current Global baseline, reuse the previous dependency cache where possible, run tests/build, check idle interview/workload gates, retain a rollback image and recreate Web only. Verify public HTML, version marker, carousel controls and unchanged core container identities after release.
