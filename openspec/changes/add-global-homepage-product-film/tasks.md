## 1. Media and Page Implementation

- [x] 1.1 Verify the supplied MP4 codecs, audio stream, dimensions, duration, size, and poster.
- [x] 1.2 Copy the MP4 and poster into the Global Web public media directory without removing the audio track.
- [x] 1.3 Add the English homepage film section and accessible native-player attributes.
- [x] 1.4 Add responsive film presentation styles for desktop and mobile.
- [x] 1.5 Add an explicit cached Global Nginx `/media/` route.

## 2. Regression Verification

- [x] 2.1 Add regression coverage for copy, media paths, required player attributes, and absence of autoplay.
- [x] 2.2 Run focused tests, full Global Web tests, copy audit, typecheck, and production build.
- [x] 2.3 Validate the OpenSpec change strictly and record the release/rollback procedure.

## 3. Production Deployment

- [x] 3.1 Capture the Global production baseline and confirm the deployment activity gate is idle.
- [x] 3.2 Create a scoped release and recreate only the Global Web service.
- [x] 3.3 Verify production homepage markup/bundle, media and poster responses, byte ranges, build marker, health, and unchanged core/China services.
