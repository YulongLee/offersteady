## Decisions
Reuse global-product-film styles. Place the tutorial after workflow and before capabilities. Use native controls, muted, playsInline and metadata preload without autoplay. Copy the supplied 49-second 1080p H.264/AAC video and poster without transcoding or stripping narration.
## Risks
Optional video transfer is 7.8 MB; metadata preload and no autoplay limit unsolicited transfer. Preserve all existing sections and do not deploy the dirty workspace wholesale.
## Deployment
Compare App.tsx with production, overlay only that file and two assets onto the current Global release, retain rollback image, check idle activity before build and cutover, recreate Web only, verify public files/ranges/hash and unchanged core container identities.
## Non-goals
No new navigation, partner program, pricing or business behavior. No Chinese deployment.
