## Context

The supplied international product film is a 36-second 1920×1080 H.264 MP4 with an AAC audio track and a matching JPEG poster. OfferSteady Global is a Vite application served by Nginx, whose public static routes are allow-listed and otherwise return 404. The homepage currently contains the hero, workflow, capabilities, responsibility statement, and footer.

## Goals / Non-Goals

**Goals:**

- Present the English product film as a polished, responsive homepage section.
- Preserve its music and sound effects while starting playback muted.
- Prevent the media asset from increasing the JavaScript bundle or eager-loading the full video.
- Deploy and roll back the Global Web container independently.

**Non-Goals:**

- Changing the film, product copy outside the new section, or any core product workflow.
- Adding autoplay, analytics, a third-party video host, or backend media processing.
- Changing the China site or restarting the Global Backend, Admin, worker, database, or Redis services.

## Decisions

1. Store the MP4 and poster under `apps/web-global/public/media`. Vite copies these files byte-for-byte and Nginx can serve them without application or backend work. A third-party host was rejected because it introduces tracking, availability, and review dependencies.
2. Use the browser-native `<video>` element with `controls`, `muted`, `playsInline`, and `preload="metadata"`. This preserves user control, works on desktop and mobile, and avoids a player dependency. Autoplay was rejected because it is disruptive and often blocked.
3. Add an explicit `/media/` Nginx location with immutable caching and `try_files`. This prevents the final deny-by-default location from masking media files while keeping unknown routes closed.
4. Place the film immediately after the hero. Visitors can understand the product before reading detailed workflow and capability sections.
5. Build and recreate only the Global Web service from a release derived from the current Global production baseline. Container identity checks verify that core services and the China deployment are unchanged.

## Risks / Trade-offs

- [The 4.6 MB file consumes bandwidth when played] → Load only metadata initially and apply long-lived cache headers.
- [Some browsers remember or override muted state] → Set the HTML muted property and leave sound activation to native controls.
- [A missing Nginx route could return the site 404 page] → Add explicit media routing and verify normal and range HTTP requests in production.
- [The working tree contains unrelated changes] → Deploy a scoped overlay against the current Global production release rather than the entire local tree.

## Migration Plan

1. Validate the source codecs, audio stream, poster, UI tests, typecheck, and production build.
2. Confirm no active interview/desktop/queue work before replacing the Web container.
3. Copy the current Global release to a new immutable release, overlay only the reviewed files, and build/recreate only Global Web.
4. Verify the homepage, MP4, poster, range requests, build marker, service health, and unchanged core container identities.
5. Roll back by restoring the previous release symlink and previous Global Web image if any check fails.

## Open Questions

None.
