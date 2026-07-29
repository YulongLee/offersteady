## 1. Index control

- [x] 1.1 Add `X-Robots-Tag: noindex, follow` to login, error, and authenticated application routes.
- [x] 1.2 Keep the homepage indexable and keep application routes outside the sitemap.

## 2. Social metadata

- [x] 2.1 Add complete Open Graph metadata using existing homepage facts.
- [x] 2.2 Add a summary-large-image Twitter Card.
- [x] 2.3 Export the approved 1200x630 SVG share card to PNG and update the asset manifest.

## 3. Asset caching

- [x] 3.1 Add a one-year immutable cache policy to fingerprinted public assets.
- [x] 3.2 Preserve short-lived HTML behavior and existing security headers.

## 4. Regression coverage

- [x] 4.1 Extend the SEO regression script for noindex, social metadata, image dimensions, and immutable caching.
- [x] 4.2 Run focused Web tests and the production build.
- [x] 4.3 Validate Nginx syntax and live HTTP behavior.
- [x] 4.4 Run strict OpenSpec validation.
