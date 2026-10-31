# CN mock static release delta

This tool assembles public files only. It performs no SSH, Docker action, deployment,
private configuration read, real interview, model call or Git write. The production
controller must enforce fresh component ownership, full inventories, original nginx
inputs, fixed images, idle-user gates, rollback and live acceptance separately.

The reviewed input is the complete 353-file static directory from the actual running
Web image `sha256:99822e10e7b516aefe4ad96248f9eea631d90b057cb77b8dd386cff4830516fb`.
Every file is compared with the fresh server manifest; symlinks are rejected. Source
inputs are the three Web hashes in the frozen combined handoff. Local `dist` is never
used.

## Delta algorithm

- Parse the actual mock module and replace only its `MockInterviewPage` function body
  with the frozen source body compiled to classic ES2020 React calls. Preserve the
  original React hooks, router, auth, HTTP/WS transports, quote refresh, indicator,
  phase labels and report component. Actual main export `x` is HTTP and `S` is WS URL.
- Select only the new player/error classes and two player constants from the frozen
  client into a standalone module. The page and test client share that exact module
  and therefore the same error constructor identity. The original player remains
  available for unrelated callers.
- Append exactly the three compact-instructions CSS rules to the actual mock CSS.
- Reversion the reverse dependency graph (12 JS + 1 CSS) so immutable cache URLs are
  fresh. Parent modules change only reference strings; reverse rewriting recovers
  their original bytes. All old immutable assets are retained for open clients and
  rollback. Only index/guide/privacy/terms resource references and build version
  change in existing mutable files. SEO documents, main CSS, media, resume,
  multi-screen, Word export, and state-read initialization remain present.

## Build and verify

```sh
python3 tools/cn_mock_web_release/build_web_release.py \
  --baseline artifacts/cn-mock-20261101-release/web-baseline \
  --baseline-manifest artifacts/cn-mock-20261101-release/baseline-public.json \
  --source-manifest artifacts/cn-mock-server-local-20261031/combined-source-manifest.json \
  --output artifacts/cn-mock-20261101-release/candidate-web
python3 tools/cn_mock_web_release/verify_package.py \
  --baseline artifacts/cn-mock-20261101-release/web-baseline \
  --baseline-manifest artifacts/cn-mock-20261101-release/baseline-public.json \
  --source-manifest artifacts/cn-mock-server-local-20261031/combined-source-manifest.json \
  --candidate artifacts/cn-mock-20261101-release/candidate-web \
  --output artifacts/cn-mock-20261101-release/candidate-web-static-verification.json
node tools/cn_mock_web_release/verify_runtime.mjs \
  artifacts/cn-mock-20261101-release/candidate-web \
  artifacts/cn-mock-20261101-release/candidate-web-probe
python3 -m unittest discover -s tools/cn_mock_web_release -p 'test_*.py' -v
node --test tools/cn_mock_web_release/test_runtime_patch.mjs
```

The build output must be empty. Static verification reproduces every candidate byte
from the frozen inputs, checks all inventories, and verifies nonmock parent reversal
and original report/Word hashes. Every new JavaScript file is syntax checked.

Runtime verification extracts the actual compiled candidate page/report plus its
transitive module-local declarations without importing the application bootstrap.
A React/router host bridge permits jsdom to mount them with the test React dispatcher.
The existing page tests retain their mocked HTTP seam and Word-download boundary;
this is not a live backend integration test. Player tests import the exact new
candidate module. Two additional direct transport tests execute the original actual
HTTP function with synthetic fetch (headers/body/errors) and actual WS URL helper,
and assert shared player/error class identity. No production or model call occurs.
Successful evidence includes the exact candidate manifest hash and JUnit report.

The candidate directory is `web/html/` plus two public metadata files. Overlay only
`web/html/` onto the fixed actual Web base image; never overwrite nginx or entrypoint
configuration. Retain metadata outside the served HTML root for controller checks.
