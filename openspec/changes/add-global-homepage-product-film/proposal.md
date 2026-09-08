## Why

OfferSteady Global now has a finished English product film, but visitors cannot watch it on the international site. Publishing it on the homepage provides a concise product walkthrough while keeping the existing application and backend paths untouched.

## What Changes

- Add a dedicated product-film section to the OfferSteady Global homepage.
- Serve the supplied H.264/AAC MP4 and matching poster as first-party static assets.
- Use a native, responsive player that starts muted, exposes playback controls, supports inline mobile playback, and loads metadata only until the visitor chooses to play.
- Deploy only the Global Web service and retain the current release as the rollback baseline.

## Capabilities

### New Capabilities

- `global-homepage-product-film`: Covers homepage presentation, player behavior, media delivery, and release isolation for the English product film.

### Modified Capabilities

None.

## Impact

- Affects `apps/web-global` homepage markup, styling, public static media, and the Global Web Nginx static-route configuration.
- Adds no runtime dependency, API, database, authentication, interview, AI, ASR, RAG, Companion, billing, or China-site behavior.
- The MP4 is approximately 4.6 MB and remains unloaded beyond metadata until playback, limiting impact on initial page performance.
