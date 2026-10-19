# Global authentication/state release support — 2026-10-17

This directory supports `scripts/release_global_auth_state.py`. The private
server release directory is
`/opt/offersteady-global/releases/20261017-global-auth-state-1`; its Docker
project/container are `offersteady-global` / `offersteady-global-backend-1`.
The controller binds the actual baseline container
`c2b7caa35c86c85c13c4f9baeebb1da30465562d4ad50126c56db3d141d5bd4e` and image
`sha256:b31a810a49f718e360f8ddbcbae0e7aa3d0184012b8993cd0e2f5f973bc7657a`.

The runtime patch is exactly the eight approved auth/state source paths. The
complete baseline inventory contains 236 app/Prompt files, including 74 Prompts.
No CN source, commercial rule, model, feature flag, desktop artifact, migration
or dependency is introduced. The Global mock flag and regional rules remain
bound by the candidate source/configuration checks and synthetic tests supplied
by the parent release packager.

## Frozen inputs

`input.json` binds the baseline IDs, exactly eight payload SHA values, the full
236-file baseline inventory and the five Global gate paths. Its `verified` object
has exactly these keys:

```json
{"candidateTests": 1, "additionalSubtests": 0, "skipped": 0, "syntheticOnly": true}
```

These example counts describe the schema only. The release packager must supply
the actual candidate counts; the controller does not reuse CN or previous Global
counts. `candidateTests` must be positive and the other counters nonnegative
integers. `candidate-verification.json` must carry identical typed count values,
`passed: true`, `sourceFrozenAfterTests: true`, the exact eight `candidateHashes`
and nonempty successful `records`. The verification report itself is SHA-bound.

Nine support files are required under `supportFiles`:

- `release_global_auth_state.py`, preserving this basename.
- `candidate-verification.json`.
- `probe/candidate-probe.py` and `probe/probe-expectations.json`.
- `legacy-gates/check-idle.py`, `legacy-gates/check-mock-idle.py`,
  `global_mock_companion_idle_gate.py`, `extra_idle_gate.py` and
  `active_work_gate.py`.

All five gate files are byte-identical copies of the reviewed previous Global
release. They keep Global identity checks and only read aggregate database/Redis
state. They do not resolve stale work or mutate production records.

## Release protections

The controller retains the previous Global deployment-context implementation.
Every actual Compose/Env file is copied privately in original order; original
and frozen bytes and complete renders are checked again. The current actual
context has five Compose files and one Env file. Historical overlays are
preserved. The only new overlay is `compose.auth-state.json`, selecting the new
immutable Backend image. Six non-target container identities are frozen by the
parent's actual runtime inventory and checked by the generic controller.

Preparation requires healthy/running/restart-zero state, actual baseline source,
matching bare-image source and original image layers. Candidate execution uses
no network, a read-only filesystem, removed capabilities and no-new-privileges.
The `offersteady-global-backend` shared tag is inspected and frozen without
changing it. New baseline/candidate/rollback tags are release-specific.

The isolated probe has its own 151-path `api_router` shell expectations. Runtime
validation separately compares all 215 live HTTP paths and the complete OpenAPI
schema SHA using sorted keys, compact separators and `ensure_ascii=True`.
`liveHttp` / `liveOpenapiSha` must be supplied from the actual server; the
controller never uses the offline shell map as the full application map.
Preparation and every pre-cutover revalidation check the complete live schema.
Public checks use `offersteady.com`, and only Global Web/Admin Nginx may be
reloaded if the Backend IP changed.

Every forward switch and rollback rechecks protected work. Automatic recovery
uses temporary read-only containers on the fixed original image, original
network and frozen runtime environment. The private environment and original
container snapshot are SHA-bound before use. The same five gate bytes run
without mounting volumes, publishing ports or starting app.main, so recovery
checks do not depend on a broken candidate's source/environment/health.
Unknown state, new work, altered recovery context or a later deployment stops
recovery instead of overwriting another owner or interrupting active interviews.

## Local verification

Run from the repository root:

```text
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q -p no:cacheprovider scripts/release_support/global_auth_state_20261017
```

The current suite has 273 passing checks: 135 synthetic controller checks,
128 synthetic Global activity-gate regressions and 10 actual frozen-candidate
probe acceptance, tamper-refusal and IO-guard checks. Docker, HTTP, application probes,
PostgreSQL and Redis are replaced by synthetic boundaries in the controller/gate
tests; the candidate probe runs the actual frozen application without external IO. Tests cover typed
candidate-report bindings, exact source/support/baseline scope, full live schema,
Global five-file/one-env context, shared tags, six non-target containers, activity
and unknown metadata, backend-only switching, ownership and independent recovery.
These checks do not constitute application-candidate tests, a production rollout,
a production rollback rehearsal or a measured live P95 improvement.
