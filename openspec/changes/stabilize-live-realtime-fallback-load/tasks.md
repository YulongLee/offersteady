## 1. Baseline and web recovery

- [x] 1.1 Add regression tests reproducing fallback snapshots during an in-flight/connected SSE subscription.
- [x] 1.2 Add a transport-connected subscription signal and stop fallback work while the stream is connected or connecting.
- [x] 1.3 Replace the fixed one-second loop with non-overlapping bounded exponential-backoff recovery.

## 2. Backend event-loop isolation

- [x] 2.1 Offload synchronous work for high-frequency realtime snapshot, heartbeat, device-status, active-connection, and capture-control routes.
- [x] 2.2 Add concurrency regression tests proving a blocked repository call does not stall an unrelated async request.

## 3. Verification

- [x] 3.1 Run focused web and backend tests plus typechecks/builds for affected applications.
- [x] 3.2 Run synthetic recovery/load verification and record pre/post request amplification evidence.
- [x] 3.3 Run strict OpenSpec validation and confirm no deployment or production mutation occurred.
