# CN mock Backend release overlay

This tool prepares an incremental context; it does not SSH, deploy, read private configuration or run a model. The release controller must independently validate live ownership, user-work gates, image configuration and layer ancestry.

```bash
python3 tools/cn_mock_release/build_backend.py \
  --baseline <fresh-public-backend-probe-baseline.json> \
  --baseline-source <fresh-extracted-backend-root> \
  --handoff artifacts/cn-mock-server-local-20261031/combined-source-manifest.json \
  --output <new-empty-directory>
```

The flat baseline contract contains `image`, complete `inventory`, `python`, raw distribution-name `dependencies`, complete effective `settingsSha256`, complete `openapiSha256`, and `httpPaths=203`. Extra container-signature metadata is ignored. Existing source hashes are checked against fresh extracted bytes and the four existing files; all five new hashes must match the frozen source handoff. Only `mock_interview_diagnostics.py` is added. No dependency installation, configuration change or unrelated source rebuild is included.

Before building, the server controller must pin `offersteady-cn-backend-baseline:mock-20261101` to `backend-manifest.json.baseImage` and verify that alias resolves to exactly that image before and after the build. Build with `--network=none --pull=false`; check candidate image Config equality and original RootFS layer prefix. Bare `FROM sha256:...` is deliberately avoided because BuildKit can interpret it as a repository name.

The generated `candidate-probe.py` is run through the candidate image's Python with `-B -`, `/app/apps/backend` as working directory, `--network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges`, the unchanged server-local environment file, and `OFFERSTEADY_RELEASE_PROBE_IMAGE` set to the fixed candidate image ID. That environment file must remain on the server and must never enter this context or output.

The probe checks the entire resulting runtime inventory, all Python syntax, exact dependencies/Python/effective-settings/OpenAPI digests, 203 HTTP paths, pool-disabled state and mock quota/deadline constants. It executes actual CN/Global runtime submission policy, microphone cleanup/replacement routes and pure HTTPX MockTransport cases with synthetic inputs. Audit hooks deny external network/database calls and writes. Four controlled synthetic worker threads are expected, including executor shutdown; all must terminate. Stdout contains only a stable JSON summary without timings, random trace IDs, environment values or user data.

Local tool validation:

```bash
PYTHONPATH=apps/backend python -B -m unittest discover -s tools/cn_mock_release -p test_backend_build.py -v
```

Tests cover frozen/old source drift, scope/path/symlink rejection, nonempty output preservation, syntax failures, ignored private metadata, complete unchanged input preservation, and guarded actual runtime/provider scenarios in an isolated child process. These checks supplement the actual-image probe; local Python/configuration results are not substitutes for the server's real candidate-image validation.
