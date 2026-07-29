# Design: Public SEO indexability

## Context

OfferSteady is a React SPA served by Nginx. The existing catch-all `try_files` rule returns `index.html` for every path, including invalid URLs and SEO control files. The landing-page content is already mature and should not be redesigned.

## Decisions

### Use an explicit Nginx route allowlist

Nginx serves the SPA shell only for routes currently defined by the React router. Dynamic interview routes are matched by a bounded regular expression. Static assets and SEO resources are matched first, and the final location returns HTTP 404.

This is preferred over returning HTTP 200 and relying on the React 404 component because crawlers need the status code before JavaScript runs.

### Use build-time initial HTML instead of changing the React prototype

The Vite entry document contains a semantic landing-page snapshot inside `#root`. React replaces that snapshot with the existing landing component at startup. The snapshot reuses current product statements and does not add a new UI state or API dependency.

This is a minimal static-generation boundary for the only public canonical page. A future change may introduce route-aware SSG if more public pages are approved.

### Keep structured facts conservative

JSON-LD includes only verifiable Organization, WebSite, and SoftwareApplication facts already visible in the product and support information. It does not include ratings, user counts, unsupported offers, or FAQ rich-result markup.

## Risks

- The static snapshot and React landing copy can drift. A focused regression script checks the required SEO contract; future copy changes should update both representations together.
- An application route added only in React could return 404 until added to the Nginx allowlist. Route additions must update the allowlist and regression test in the same change.
- The JSON-LD inline block must remain covered by the CSP hash when its contents change.
