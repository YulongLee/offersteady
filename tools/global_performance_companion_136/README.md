# Global performance and companion1.3.6 release controller

The new controller is `scripts/release_global_performance_companion_136.py`.
It executes only on the authorized Global host and never runs a historical
prepare/deploy/rollback entrypoint. `base_helpers.py` is the reviewed Global
20261022 helper copy; `ownership_primitives.py` contains AST-extracted helper
functions only, with no historical mutation entrypoints. The original seven
aggregate gates and TCP gate are retained. Full snapshots/settings remain on
the server. Tests must never call real Docker, SSH, providers or databases.

The fixed server root is:

```text
/opt/offersteady-global/releases/20261102-global-performance-companion-136-1
```

Deploy a flat support layout there: `controller.py` (copy of the new controller),
`base_helpers.py`, `ownership_primitives.py`, `probe.py`, all seven gate paths
(including `legacy-gates/`) and `backend_tcp_idle_gate.py`. Local source helpers
are in `scripts/release_support/global_performance_companion_136/`.
The parent executor must check the reviewed SHA of **every support file and
input.json before every command**. The controller rechecks the support hashes
inside input.json on each action, and prepared.json binds the input bytes.

## Input contract

`input.json` has exactly these keys. All inventory entries are relative public
file paths mapped to SHA-256, and every image is a full immutable `sha256:...`.

```json
{
  "releaseId": "20261102-global-performance-companion-136-1",
  "baselines": {
    "backend": {
      "id": "actual pinned backend id from controller BASES",
      "image": "actual pinned backend image from controller BASES",
      "startedAt": "actual original StartedAt",
      "signature": {},
      "inventory": {},
      "settingsSha256": "canonical Settings.model_dump(mode=json) SHA",
      "settingsFields": 0
    },
    "web": {
      "id": "actual pinned web id from controller BASES",
      "image": "actual pinned web image from controller BASES",
      "startedAt": "actual original StartedAt",
      "signature": {},
      "inventory": {},
      "nginxSha256": "actual /etc/nginx/conf.d/default.conf bytes SHA"
    }
  },
  "nonTargets": {"five exact Global non-target names and the fixed historical stopped container": {}},
  "candidates": {
    "backend": {"image": "sha256:...", "rollbackImage": "sha256:...", "inventory": {}, "rollbackInventory": {}},
    "web": {"image": "sha256:...", "rollbackImage": "sha256:...", "inventory": {}, "rollbackInventory": {}}
  },
  "allowedBackend": {"the eight approved Python paths and current/history Global JSON paths": "exact new SHA"},
  "allowedWebChanged": ["index.html", "other actually changed HTML", "offersteady-global-build.json if changed"],
  "globalManifest": {"path": "input/global_desktop_release_manifest.json", "sha256": "exact manifest bytes SHA"},
  "objectsReadback": [],
  "openapiBefore": {"path": "input/openapi-before.json", "schemaSha256": "canonical complete schema SHA", "pathCount": 223},
  "openapiAfter": {"path": "input/openapi-after.json", "schemaSha256": "canonical complete schema SHA", "pathCount": 223},
  "supportFiles": {"controller.py": "SHA", "every other exact support path": "SHA"},
  "publicRoutes": {"/": "index.html", "/login": "index.html"}
}
```

`signature` and each non-target value are the exact output of the reviewed
`base_helpers.container_signature()` calculated on the server. They contain
hashes, lifecycle/network metadata, never raw Config/HostConfig/Env. Mounts are
canonically sorted as **whole objects**, retaining every field and duplicate.
Baseline Backend has302 inputs; Web235. New and rollback Backend303 inputs add
only `global_desktop_release_history.json`; current JSON is already in302.
The complete host container set is the seven Global services plus the exact
historical stopped build container `zealous_bhaskara`. Its full signature was
matched read-only against the October22 frozen non-target record. The release
pins its original ID/image, September7 StartedAt, running=false, restart0 and
all configuration/mount/network digests. It is the sixth protected non-target;
this release never starts, removes, replaces or cleans it. Any additional
container, missing expected name, signature change or lifecycle change stops
preparation/verification. Prepare checks this stopped signature before freezing
any target. All seven user-work gates and target scope remain unchanged.

The approved Backend set is exactly the eight paths in controller BACKEND_FILES
plus `apps/backend/app/global_desktop_release_manifest.json` and
`apps/backend/app/global_desktop_release_history.json`. The new full inventory
must differ at precisely those ten paths, and all other bytes must match.
Rollback Backend differs from actual baseline only in `modules/web.py` (solely
the exact historical lookup compatibility), history JSON, and the same new136
current manifest. It removes performance/scoped-query changes while preserving
old135 and current136 download URLs. The root reviewer must verify the rollback
web.py change is only that compatibility helper; the controller binds its exact
provided full inventory and image.

New Web retains all235 baseline paths and may change only declared HTML/build
marker files. Every new path is an `assets/*.js`; the static graph builder must
prove it is solely the exact download metadata/resource-reference closure.
Rollback Web is all original bytes plus those new JS assets unchanged. Nginx
input trees in actual/base/new/rollback images must be identical.

`objectsReadback` is exactly three uploader reports, each containing target,
`version`, `fileName`, `fileSizeBytes`, `sha256`, `objectKey`, `contentType` and
`objectReadbackVerified=true`, matching the candidate manifest. The exact Global
filenames, namespace, protocol2.0, version1.3.6, minimum OS and truthful trust
fields are checked. Mac must be verified/notarized; Windows unsigned/notarized
false. No local paths are accepted in published manifest entries.

Complete schema documents are compared after removing only the new optional
`sessionId` and `requestId` query parameters from the existing device next GET.
Everything else, including all existing paths/operations/components, must be
identical. Rollback is checked against the complete before schema.

## Candidate probe

Backend agent supplies `probe.py`, executed on the actual candidate with
network-none/read-only, original private environment and a read-only release
mount. CLI:

```text
python -B - --baseline-settings /release/backend/settings-before.private.json --baseline-schema /release/input/openapi-before.json
```

Prepare runs this against both Backend images. The compatibility rollback image
uses the same arguments plus `--rollback`, requiring the original complete
schema and preserved history lookup instead of new performance/query methods.
Results are saved separately as `backend/offline-probe-new.json` and
`backend/offline-probe-rollback.json`.

It must produce exactly:

```json
{"passed":true,"checks":["stable_lowercase_check"],"providerCalls":0,"databaseWrites":0,"workersStarted":0,"lifespanStarted":false,"settingsUnchanged":true,"schemaAllowedDelta":true}
```

No app factory/lifespan, real model, repository constructor, user content,
network or DB connection may execute. Complete effective Settings must remain
identical; no new dependency, pool flag, commercial or model setting is added.

## Actions and recovery

`python controller.py` defaults to `preflight`; `prepare` freezes private actual
Compose/Env/configuration and validates candidates without changing services.
`preflight` rechecks prepared inputs, runtime, all seven gates and TCP only.
Audit files/lock live in this private root; these are not business mutations.
Only explicit `deploy` switches Backend then Web, each with fresh gates and
fixed-image frozen context. `verify` independently checks known final state.
If receipt is lost, rerun preflight/verify to inspect actual ownership; completed
switches are adopted from a matching saved intent and never blindly restarted.

`rollback` checks exact ownership/source/configuration and fresh gates before
each change. It can start a twice-proven owned original container that Compose
stopped before creating a candidate, without resetting the original financial
anchor1792604406734. Unknown/drifted/busy states stop, never end user work.
Every Global financial reservation remains protected; no CN orphan exception
is imported. Backend IP changes may require only an existing static-upstream
Nginx reload of Web/Admin after complete gates and config/tree checks. No other
Admin change/recreation is permitted.

Root must additionally execute real public Range/full downloads for all six
exact old135/current136 filenames, all changed static files and bounded
sanitized error counts. Controller public route checks do not claim those
separate acceptance steps were performed. Git pushes and CN deployment are
outside this controller.

## Local input assembly

`assemble_input.py` reads final evidence only and copies the reviewed twelve
support files into a local flat payload. It has no remote, subprocess,
prepare/deploy or provider action. Run from the repository root:

```text
python tools/global_performance_companion_136/assemble_input.py --report artifacts/global-performance-companion-20261102/controller/input-assembly.json
```

Defaults are `artifacts/global-performance-companion-20261102/` for actual
baseline signatures/public boundary, private Settings digest summary, complete
schema `openapi-after.json`, final `backend-images.json`/`web-images.json`, Web
graph manifest, current Global136 manifest and three `*-oss.json` reports.
The exact legacy stopped-container signature also requires the independent
`legacy-stopped-container-preservation.json` proof, including a positive match
against the previously frozen October22 non-target and current running=false.
Original actual inventories and full schema are read from
`artifacts/global-performance-20261102/`. Desktop handoff, three source maps
and package proofs are read from
`artifacts/global-companion-1.3.6-20261102/`; public metadata and independent
package proofs are cross-checked with the corresponding release artifacts.
`--repo`, `--artifact-root`, `--desktop-root`, `--openapi-after` and `--output`
can explicitly select local locations. No intermediate image or synthetic
schema fallback exists. Full private Settings/environment are never copied.

The assembler checks all twelve fixed support hashes, final new and rollback
image full inventories/config-layer proofs, both actual-image offline probe
results, complete schema baseline/delta, exact public metadata/artifact/OSS
agreement, Mac signature/notarization and truthful Windows unsigned evidence,
and all94 common source inputs/all27 common non-native runtime files. It then
runs only the controller's local `check_plan()` against staged files before
atomically creating `payload/`. Missing or mismatched evidence rejects the
assembly. An existing identical payload is reused; a different payload is
preserved and rejected. `input-assembly.json` binds every payload/source file
SHA for the root executor's independent review and remote source checks.

Public routes use `/` and `/login` for the homepage, the15 other modified
canonical page URLs,16 new `/assets/*.js` URLs and the build marker. The
original Nginx intentionally rejects explicit `/index.html` and nested
`/.../index.html` URLs. They must never be added to public acceptance routes.
All original235 static paths remain in the image independently of URL access.

Run the entirely synthetic assembler/controller checks with:

```text
python -m pytest -q tools/global_performance_companion_136/test_assemble_input.py scripts/test_release_global_performance_companion_136.py
```
