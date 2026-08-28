## Why

The live interview page currently exposes a prominent “设备正在重连” alert when runtime freshness becomes stale even though desktop capture may still be healthy. This false or transient infrastructure warning undermines user confidence during an interview and should be handled through silent recovery and operator diagnostics instead of a user-facing interruption.

## What Changes

- Keep transient desktop transport and source recovery internal during an active interview; do not render reconnect wording, a global reconnect alert, or a recovery action to the user.
- Stop inferring `reconnecting` merely because a live runtime is temporarily `preparing` or lacks a recent signal while capture remains reported as healthy.
- Preserve explicit user-actionable notices for permission denial and unrecoverable device errors.
- Preserve reconnect state and diagnostics for Backend, desktop, logging, and operational investigation.
- Add regression coverage for healthy live silence, real reconnect recovery, and actionable permission/error states.
- Non-goals: changing the approved live layout, desktop companion UI, ASR endpointing, transcript timing, or deployment/release packaging.

## Capabilities

### New Capabilities

- `silent-live-recovery-experience`: Defines how live capture recovery remains operationally observable without exposing transient internal recovery warnings to interview users.

### Modified Capabilities


## Impact

- Web runtime-to-capture-state mapping and live-page status presentation.
- Web adapter and application-state regression tests.
- Backend and desktop recovery protocols remain compatible and unchanged.
- No raw audio, transcript content, API keys, or personal information is added or persisted.
