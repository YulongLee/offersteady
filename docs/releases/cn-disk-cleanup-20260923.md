# CN disk maintenance — 2026-09-23

User-authorized removal of unused server artifacts. Completed at approximately
04:10 Asia/Shanghai. No application code/configuration change, deployment,
container restart, database mutation or Global operation was performed.

## Measured result

| Measure | Before | After |
| --- | ---: | ---: |
| Root filesystem used bytes | 39,256,260,608 | 9,681,330,176 |
| Dashboard disk usage (used / total) | 74.85% | 18.46% |
| Ordinary available bytes | 10,826,579,968 | 40,401,510,400 |
| `df` usage (excludes reserved blocks from availability) | 79% | 20% |
| Expanded release directories | 27 | 5 |
| Release-directory allocated bytes | 6,506,700,800 | 1,743,024,128 |
| Docker image count (`docker system df`) | 29 | 16 |
| Build cache records | 698 | 0 |
| Containers / volumes | 8 / 8 | 8 / 8 |

Net filesystem space reclaimed: **29,574,930,432 bytes (27.54 GiB)**.
Docker image and cache sizes share layers and must not be added together to
estimate savings; the filesystem before/after measurement is authoritative.

## Removed artifacts and recovery

- Removed tags and image records for 12 identified obsolete product images,
  plus Docker-confirmed dangling image/intermediate records. Removal used no
  forced image deletion; all images referenced by containers were protected.
- Cleared unused build cache using Docker's own garbage collection. Two
  initial passes retaining 1 GB did not release most shared cache records; the
  final all-unused-cache pass released them. No containerd storage directories
  were manually removed. Future builds may need to regenerate cache.
- Removed 22 explicitly named obsolete expanded release directories and five
  obsolete release symlinks after checking current/previous pointers, Docker
  bind mounts, Compose source labels and process working directories.
- Before removing these directories, preserved their source/configuration and
  other non-dependency files in a verified archive. Reproducible `node_modules`,
  Python virtual environments and language/test caches were excluded.

Private archive on CN host:
`/opt/offersteady/maintenance-archives/20260923-disk-cleanup/retired-release-sources.tar.gz`.
Archive size: **519,708,769 bytes**. Directory permissions `0700`, archive `0600`.
Gzip integrity, archived root coverage and SHA-256 verification passed.
Configuration secrets remain on the server and were not printed or copied into
this repository. Older source/configuration can be recovered from the archive;
removed dependency caches and obsolete images require rebuilding, not undelete.

## Retention exceptions protecting operation and rollback

Current/rollback Web and Backend images remain unchanged, including the
compatibility-safe rollback documented in
[the quick-stage release](./cn-quick-stage-completion-20260923.1.md).
Also retained running service images, the prior Admin and material-worker images,
required current-image build base, and Python/Node/Nginx base images.
Sixteen image records do not represent sixteen redundant application releases.

Five expanded source directories remain:

- `20260923-cn-quick-stage-1`: current application.
- `20260923-cn-quick-stage-rollback-1`: tested compatibility-safe rollback.
- `20260923-cn-web-nothink-1`: direct baseline referenced by current release tooling.
- `20260922-cn-pdf-processing-reliability-1`: active material-worker Compose source.
- `20260911-cn-alipay-review-login-1`: active analytics Compose source and previous pointer.

All eight volumes, all database backups (862,326,784 allocated bytes), business
data, runtime logs, current static assets and desktop downloads were left alone.
No `system prune`, volume pruning, `down`, restart, recreation or database cleanup
was executed. This was one-time maintenance; no scheduled deletion policy or
persistent Docker configuration was installed.

## Post-maintenance verification

- All eight original container IDs, image references, start timestamps and
  restart counters remained unchanged; running/health conditions passed.
- Backend/Web rollback tags still resolve to the expected protected digests.
- Current source pointer remains `20260923-cn-quick-stage-1`.
- Public `/`, `/app`, `/healthz`, `/api/v1/web/state`, `/api/v1/billing/status`
  and `/offersteady-build.json` each returned HTTP 200.
- Archive SHA-256 verification passed after deletion.
- No product test suite was rerun because no runtime code was changed. Checks
  establish post-maintenance availability, not full interview/provider acceptance.

Local one-time guarded maintenance/verification scripts were kept under
`/tmp/offersteady-cn-disk-cleanup-NFksrL`; they are audit aids, not recurring jobs.
