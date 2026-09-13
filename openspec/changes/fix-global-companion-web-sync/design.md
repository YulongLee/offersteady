## Context

The Companion already registers, heartbeats and publishes over the Global API. The Web preparation view only loaded its binding during mount, while `getDesktopDeviceBinding` swallowed every error. A transient API failure therefore looked identical to an unbound session. Production also had Web and Backend containers labelled with different release directories, allowing healthy but incompatible application versions to run together.

## Decisions

1. Poll the authoritative binding endpoint every five seconds only while the preparation view is mounted. A local in-flight guard prevents overlapping reads, and cleanup stops the timer.
2. Attach HTTP status to `AppError` instances created by the JSON client. A 404 remains a normal unbound result; other failures are surfaced and retried instead of clearing a valid binding.
3. Validate the Compose working-directory label for Global Web and Backend after `docker compose up`. A mismatch fails the deployment before public acceptance checks complete.

## Non-Goals

- No changes to the desktop capture protocol or ASR transport.
- No forced Companion upgrade or user data changes.
- No production deployment as part of local implementation.
