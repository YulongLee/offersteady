## Why

The running Global Web still issues duplicate short-lived `/api/v1/web/state` reads. These requests add avoidable tail latency and backend load even though the Global backend already has the lightweight heartbeat and request-breakdown improvements. The Global Web already has the approved five-second transcript-render telemetry sampling, so this change also adds regression coverage to keep that optimization from drifting.

## What Changes

- Add an adapter-level Global Web state request coordinator with public/authenticated isolation, concurrent request coalescing, a short success-only cache, and explicit forced refreshes for authoritative transitions.
- Preserve and regression-test the existing five-second non-final transcript-render sampling while retaining final revisions and existing diagnostics behavior.
- Preserve existing Global API contracts, interview behavior, billing behavior, and realtime stream behavior.

## Capabilities

### New Capabilities

- `global-web-performance`: Reduce duplicate Web state reads and diagnostic acknowledgement load in the Global Web client.

### Modified Capabilities

- None.

## Impact

- Global Web adapter, its focused regressions, and an additive protocol type declaration alignment required to rebuild the existing Global Web source.
- No Backend, database, Redis schema, model, billing, authentication, desktop companion, or API response changes.
- Production deployment is a separate idle-gated rollout; this change must not include the domestic deployment or the larger server-side `/api/v1/web/state` query redesign.
