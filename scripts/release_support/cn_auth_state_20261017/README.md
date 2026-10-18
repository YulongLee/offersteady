# CN authentication/state release controller — 2026-10-17

This support directory belongs to `scripts/release_cn_auth_state.py` and the
private server directory `/opt/offersteady/releases/20261017-cn-auth-state-1`.
It is a backend-only increment over the actual CN container
`7e3ea04495bcaec9d8c072b892dcd86a87735af4ada2f002aaef92eae1039d25`, image
`sha256:cc040a55f261a37226272c31937744e6ca4bd7a8c25e0810e360d218d41acfc0`.

The controller is derived from the reviewed CN question-prefetch controller.
Its eight-file allowlist matches the frozen local auth/state candidate. It
preserves the complete source/Prompt inventory, effective configuration,
Compose/environment bytes, mounts, non-target containers, shared image tags,
and the existing prefetch, heartbeat, ACK and billing behavior. A new image is
built without network access on the actual baseline layers. Only the backend
image is selected through `compose.auth-state.json`; no shared tag is replaced.

## Private release inputs

The parent release packager supplies these hash-bound files, preserving the
controller basename `release_cn_auth_state.py`:

- `input.json`: baseline IDs, exactly eight candidate SHA values, all 168 baseline
  app/Prompt SHA values, the exact five-gate list and SHA values for support files.
- `input/apps/backend/app/...`: the eight frozen candidate source files.
- `candidate-verification.json`: `passed: true`, `sourceFrozenAfterTests: true`,
  the same eight `candidateHashes` and exactly four zero-return-code test records.
- `verified` in `input.json`: exactly `candidateTests: 433`,
  `additionalSubtests: 16`, `globalOnlySkipped: 1`.
- `probe/candidate-probe.py` and `probe/probe-expectations.json`: the reviewed,
  isolated probe with the full source and OpenAPI expectations.
- The three `legacy-gates/*.py` files, `extra_idle_gate.py` and
  `active_work_gate.py`: copied byte-for-byte from the previously reviewed CN
  question-prefetch support. The gates only print fixed aggregate counts.

The nine required support files (controller, verification, two probe files and
five gates) must all be listed under `supportFiles`. No secrets, runtime dump or
production user data belongs in this repository or the public release output.

## Operations

`prepare` validates frozen inputs, current runtime identity, all source hashes,
health and configuration; saves private diagnostics; builds and probes the new
image; and records optional `compose-backend` tag presence and its immutable ID.
It does not restart services.

`preflight` repeats source/configuration/health/tag and protected-work checks.
`deploy` repeats the five read-only gates immediately before switching only the
backend. It validates healthy/running/restart-zero state, exact source and
settings, full HTTP route dictionary and schema equality, public health/login and all
non-target container identities. Proxies are reloaded only if backend IP changes.

`verify` also validates the frozen release inputs/configuration before inspecting
the live runtime. `prepare` and pre-cutover revalidation read the already-running
server's complete OpenAPI too: `liveHttp` contains all 195 HTTP paths and
`liveOpenapiSha` hashes the complete schema with sorted keys, compact separators
and `ensure_ascii=True`. The offline `api_router` shell retains its independent
140-path map and schema SHA; it is never mistaken for the live server's full map. `rollback` retains image/container ownership and external-config
protections, then rechecks all five activity gates before restoring the baseline.
Automatic failure recovery runs the same five gate bytes in temporary read-only
containers from the fixed baseline image, with the frozen runtime environment and
original Compose network. Both the private environment and original container
snapshot are SHA-bound during prepare and checked again before use. Recovery
gates do not use the failed candidate's source, environment, health or settings;
no volumes or ports are attached and no application service is started. A changed
owner, unavailable activity gate or new protected work prevents rollback and
produces `needs_attention`; it cannot silently restart an active interview.

## Local synthetic controller verification

Run from the repository root:

```text
.venv/bin/python -m pytest -q -p no:cacheprovider scripts/release_support/cn_auth_state_20261017/test_release_cutover.py
```

The tests replace Docker, HTTP and application probes with synthetic boundaries.
They verify exact candidate/test/support bindings, baseline scope, healthy-state
checks, complete route equality, shared-tag drift, all protected gates and failed
cutover recovery/ownership. This suite does not claim the application candidate
or production deployment passed; those have separate evidence records.
