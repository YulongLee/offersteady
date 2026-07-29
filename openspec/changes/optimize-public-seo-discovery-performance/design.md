# Design: Public SEO discovery performance

## Context

The current Vite application uses one HTML entry document for the homepage and known application routes. Nginx already maintains an explicit route allowlist, making it the lowest-risk location for route-specific index control. Vite emits fingerprinted JS and CSS names, so those files can be cached permanently without stale-deployment risk.

The approved share card already exists as a 1200x630 SVG. Some social platforms handle raster previews more consistently, so the same design is exported to PNG rather than redesigned.

## Decisions

### Apply index control at Nginx

Nginx adds `X-Robots-Tag: noindex, follow` to login, error, and application routes. The homepage remains indexable, and application routes remain accessible to users and the React router.

### Cache only fingerprinted JavaScript and CSS assets

Only Vite-generated JavaScript and CSS filenames containing an eight-character content hash receive `Cache-Control: public, max-age=31536000, immutable`. Fixed-name brand images and other public files retain ordinary cache behavior. HTML keeps `no-store`, so deployments can reference new fingerprinted files immediately.

### Keep social metadata in the static entry head

Open Graph and Twitter Card fields use the existing homepage title, description, canonical URL, and raster share card. This changes link previews only and does not add visible page elements.

## Risks

- Future fingerprinted asset types outside JavaScript and CSS will require an explicit cache-rule extension before they receive immutable caching.
- The share-card SVG and PNG can drift. Changes to the design must regenerate the PNG and update its manifest digest together.
- Route-level code splitting remains a separate performance change because it affects module loading and requires broader regression coverage.
