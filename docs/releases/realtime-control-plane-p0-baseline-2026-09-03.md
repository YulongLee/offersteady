# Realtime Control Plane P0 Baseline

- Git commit: `dfc3ca83246fe803756aae55f82e55562a30b9d6`
- Git tag: `baseline-realtime-control-plane-p0-20260903`
- Production Backend image: `sha256:2ef612b83287ed758baccd1f3d2230186efd26771039b05b3386091e9bc4da44`
- Production Backend container before rollout: `2143453806aaaca7bf7a41efd8f6e041c15c2502fda6946bba605374bdab1b55`
- Container start: `2026-09-01T22:08:01.662001536Z`

The baseline image, Git tag and legacy Redis keys must remain available until the P0 production observation window passes. Rollback restores this image/commit without deleting PostgreSQL or Redis data.
