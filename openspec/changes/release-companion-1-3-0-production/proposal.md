# Proposal: Publish Companion 1.3.0 to both production editions

## Why

The desktop companion has a validated local 1.3.0 build, but the domestic and Global download manifests still point to older releases. Publishing the same release line for both editions keeps the clients aligned with the current control-plane polling behavior and gives new downloads a single supported version.

## Scope

- Build and verify domestic 1.3.0 artifacts for macOS arm64, macOS x64, and Windows x64.
- Build and verify Global 1.3.0 artifacts for macOS arm64, macOS x64, and Windows x64.
- Upload immutable versioned artifacts to the existing OSS release prefixes.
- Update the domestic and Global release manifests atomically per edition, preserving platform entries not included in the publication.
- Verify public health, release-manifest versions, download status, hashes, and platform signing metadata after publication.

## Non-goals

- No backend interview, ASR, billing, database, Redis, or web behavior changes.
- No forced upgrade of already-running companion processes; existing installations only upgrade when the product's download/update flow is used.
- No claim that Windows is code-signed; Windows remains explicitly unsigned under the current distribution policy.
- No deletion of previous release objects or rollback assets.
