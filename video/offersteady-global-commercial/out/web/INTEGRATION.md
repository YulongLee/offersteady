# OfferSteady Global website video

Use `offersteady-global-web.mp4` for desktop and high-density screens. The 720p file is an optional lighter fallback. Both files retain the licensed music and sound effects.

```html
<video
  controls
  muted
  playsinline
  preload="metadata"
  poster="/videos/offersteady-global/poster.jpg"
  width="1920"
  height="1080"
  aria-label="OfferSteady product demonstration"
>
  <source
    src="/videos/offersteady-global/offersteady-global-web.mp4"
    type="video/mp4"
  >
</video>
```

The `muted` attribute makes the initial page load silent. Keep `controls` so viewers can enable sound themselves.
