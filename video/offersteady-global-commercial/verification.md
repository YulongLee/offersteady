# Final delivery verification

Verified September 7, 2026 against the final files. The picture timeline is exactly 36.000 seconds.

| File | Size | Picture | Audio |
|---|---:|---|---|
| `offersteady-global-commercial.mp4` | 10.36 MB | 1920×1080, H.264, 60fps, 2160 frames | AAC 48kHz, music + SFX |
| `offersteady-global-commercial-nobgm.mp4` | 10.35 MB | 1920×1080, H.264, 60fps, 2160 frames | AAC 48kHz, SFX only |
| `web/offersteady-global-web.mp4` | 4.61 MB | 1920×1080, H.264, 30fps, 1080 frames | AAC 48kHz, music + SFX |
| `web/offersteady-global-web-720.mp4` | 2.29 MB | 1280×720, H.264, 30fps, 1080 frames | AAC 48kHz, music + SFX |

- All four MP4 files completed full ffmpeg decode with exit code 0 and no decode errors. They use H.264 4:2:0 full-range output and have the `moov` atom before `mdat` for progressive web loading.
- Music-master loudness is -21.1 LUFS with -3.8 dBTP true peak and 11.8 LU loudness range. The mono analysis signal has no full-scale samples.
- All five scene boundaries pass the strict three-frame music-grid tolerance both before and after the measured 2.56-frame AAC offset. Maximum source-grid error is 2.156 frames; maximum audible-output error is 1.001 frames.
- Twelve SFX source waveforms were cross-correlated against the rendered SFX-only master. After accounting for source peak delay and the measured 2.56-frame AAC output delay, every action peak lands within 0.46 frames of its intended 60fps frame (about 7.7ms maximum error).
- The website encodes retain the AAC music/SFX track. The HTML video has `muted`, `controls`, `playsinline`, and `preload="metadata"`; users can enable audio through native controls.
- Real Chrome checks at 1280×900 and 390×844 confirmed 36.053333-second media metadata, no media errors, no horizontal page overflow, playback advancing from 1.0s to about 2.16s, successful seek to 20.4s with readyState 4, and programmatic unmute availability. Desktop and mobile captures were visually inspected.
- `npm run typecheck` passed. Visible source and captured textures used by the film contain no Han characters. The active `complete-global-english-product-experience` change is validated separately before delivery.
- Independent visual and product review is recorded in [final-review.md](final-review.md). Raw evidence is in [delivery-checks.json](out/qa/delivery-checks.json), [loudness.log](out/qa/loudness.log), and [playback.json](out/qa/web/playback.json).

## Scope boundary

Product scenes come from the real Global React/CSS application with a frozen synthetic fixture. Video editorial layers enlarge the same synthetic content for readability. This film does not verify production backend latency, model accuracy, or hiring outcomes. The supplied reference film was used for visual analysis only and is absent from the handoff package.

## SHA-256

- Music master: `7564f89639608a5b40ffd26a88841ad2c31127315ea9eee0bdf109e6f7789393`
- SFX-only master: `16e2f75fe050ec9b783875461abf0a307ff5277c67dd12750bc7b8eca01d66e6`
- 1080p web: `42cb09a287ad460ee0f165320e30b69a28fb8d408afcc23f4d067ebea06d656d`
- 720p web: `8d81fa9b6bce95f79e8b8bdf90151b793329ef6613195090da7db6cf9eebef0b`
