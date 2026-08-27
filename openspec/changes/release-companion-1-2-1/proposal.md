## Why

Companion 1.2.0 can enter a permanent audio delivery loop when the desktop process restarts into the same live interview because its local source generation resets below the backend's authoritative generation. A 1.2.1 patch release is required to deliver the verified transport recovery fixes without changing the accepted layout, icon, application identity, or interview workflow.

## What Changes

- Release the transport-loss and same-session process-restart recovery fixes as semantic version 1.2.1.
- Preserve the 1.2.0 renderer layout, product icon, Bundle ID, capture workflow, protocol compatibility, and user-facing feature set.
- Build Developer ID signed, hardened, notarized, and stapled macOS Apple Silicon and Intel artifacts using the existing application identity.
- Build and structurally verify the Windows x64 artifact while reporting its actual signing state truthfully.
- Verify that upgrades retain a stable macOS application identity so existing privacy grants can be reused where macOS permits; never claim that an Apple developer account can bypass user-controlled privacy authorization.
- Keep 1.2.0 available as a rollback package. Production publication is a separate, explicit release step after local artifact acceptance.
- After the owner's explicit approval, publish the verified immutable artifacts, atomically update the production manifest, and deploy only the compatible Backend service with a retained rollback image.

## Capabilities

### New Capabilities

- `companion-release-1-2-1`: Patch-release identity, UI invariance, signed packaging, authorization expectations, verification, and rollback contract for companion 1.2.1.

### Modified Capabilities

None.

## Impact

- Affects realtime desktop/backend recovery logic, Desktop package metadata, release documentation, generated artifacts, and release verification evidence.
- Does not change the renderer layout, CSS, product icon, prompts, billing, database schema, interview-language behavior, or default privacy behavior.
- The backend handshake adds an optional backward-compatible per-channel source-generation resume field; older clients ignore it.
- Verification uses synthetic audio and metadata-only counters and does not record interview audio, transcript text, credentials, or personal information.
- Production publication affects the Desktop download manifest and Backend container; PostgreSQL, Redis, and Web remain unchanged.
