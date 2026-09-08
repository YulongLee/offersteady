# OfferSteady Global · Website commercial

36-second English product film, 1920×1080 / 60fps. This is an isolated video project and does not modify or deploy the website.

## Deliverables

- `out/offersteady-global-commercial.mp4`: high-quality master with music and sound effects.
- `out/offersteady-global-commercial-nobgm.mp4`: identical picture with sound effects only.
- `out/web/offersteady-global-web.mp4`: 1080p / 30fps website version with music and sound effects, H.264 4:2:0 and faststart.
- `out/web/offersteady-global-web-720.mp4`: 720p / 30fps fallback with music and sound effects.
- `out/web/poster.jpg`: website poster.
- `out/web/index.html`: local responsive playback preview.
- `out/offersteady-global-website-video.zip`: website handoff bundle.
- `final-review.md` and `verification.md`: independent review and technical validation.

## Embed

```html
<video
  controls muted playsinline preload="metadata"
  poster="/videos/offersteady-global/poster.jpg"
  width="1920" height="1080"
  aria-label="OfferSteady product demonstration"
  style="display:block;width:100%;height:auto;border-radius:20px;background:#080c13"
>
  <source src="/videos/offersteady-global/offersteady-global-web.mp4" type="video/mp4">
  Your browser does not support HTML video.
</video>
```

The file includes music and sound effects. `muted` makes the first load silent; native controls let the viewer enable audio. Keep `playsinline` for mobile and `preload="metadata"` to avoid loading the full video before intent.

## Reproduce

- `npm run typecheck`
- `npm run qa`
- `npm run render`
- `npm run render:nobgm`
- Start capture from the repository root with `node_modules/.bin/vite apps/web-global --config video/offersteady-global-commercial/capture-vite.config.ts --host 127.0.0.1 --port 5188`.
- Capture from the repository root with `node video/offersteady-global-commercial/capture-product.mjs`.

The local `node_modules` symlink reuses the established Remotion toolchain. On another machine, remove the symlink and run `npm ci` in this directory. Audio sources and links are recorded in `public/audio/ATTRIBUTION.md`.
