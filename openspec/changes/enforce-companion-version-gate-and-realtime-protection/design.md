## Decisions

1. The backend reads the edition-specific release manifest and compares numeric dotted versions. A missing or malformed client version remains compatible.
2. Gate is applied at desktop binding and live/written start, so direct API callers cannot bypass the UI.
3. The heartbeat path updates the device record only; session activity is touched by web heartbeat, audio frames, and the reclamation map, avoiding an extra binding-list query per heartbeat.
4. Reuse existing download-center URL guidance instead of exposing signed object URLs in errors.

## Verification

- Unit tests cover version comparison and gate behavior.
- Backend targeted tests, web tests, typecheck and build run before deployment.
- International health and binding error response are checked after deployment; CN is not changed in this release.
