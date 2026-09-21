## Decisions

1. The backend reads the edition-specific release manifest and compares numeric dotted versions. CN treats an older, missing or malformed reported version as incompatible; Global behavior remains unchanged in this release.
2. Gate is applied at desktop binding and live/written start, so direct API callers cannot bypass the UI.
3. The heartbeat path updates the device record only; session activity is touched by web heartbeat, audio frames, and the reclamation map, avoiding an extra binding-list query per heartbeat.
4. Reuse existing download-center URL guidance instead of exposing signed object URLs in errors.
5. Keep preparation web heartbeats, desktop binding polls and the backend control-query cache on the same 10-second budget. Binding mutations still invalidate the cache immediately.

## Verification

- Unit tests cover version comparison and gate behavior.
- Backend targeted tests, web tests, typecheck and build run before deployment.
- CN health, idle-capacity gate, binding error response and preparation UI are checked after deployment.
