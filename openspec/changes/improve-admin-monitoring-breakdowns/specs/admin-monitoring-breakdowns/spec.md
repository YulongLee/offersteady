## ADDED Requirements

### Requirement: Privacy-safe request breakdowns

The admin capacity monitor SHALL classify recent requests into stable request classes and normalized route templates without retaining query strings, request bodies, user identifiers, session identifiers, device identifiers, or transcript content.

#### Scenario: Dynamic identifiers are normalized

- **WHEN** the monitor records requests whose paths contain different session, device, or capture identifiers
- **THEN** the breakdown groups them under the same route template and exposes no identifier value

#### Scenario: Sensitive request data is excluded

- **WHEN** the monitor serializes a request breakdown
- **THEN** each row contains only the normalized route, request class, count, latency summary, and status totals

### Requirement: Separate user and telemetry quality

The admin capacity response SHALL expose separate rolling summaries for user-facing control requests, background telemetry requests, recovery snapshots, and SSE stream duration; SSE duration SHALL NOT contribute to user-facing API P95.

#### Scenario: Telemetry does not hide user latency

- **WHEN** telemetry requests are slow while user-facing control requests remain fast
- **THEN** the response reports the two P95 values separately and keeps the user-facing value fast

#### Scenario: SSE duration is isolated

- **WHEN** an SSE connection remains open for a long duration
- **THEN** its duration is reported under the SSE summary and excluded from ordinary user API P95

### Requirement: Bounded route diagnostics

The admin capacity response SHALL include a bounded list of the slowest recent normalized routes, ordered by P95 descending, and SHALL preserve existing aggregate metric fields for backward compatibility.

#### Scenario: Slow routes are actionable

- **WHEN** recent requests contain multiple normalized routes with different P95 values
- **THEN** the response includes the capped slow-route list in descending P95 order with request counts and 5xx counts

#### Scenario: No recent route data

- **WHEN** no request has been recorded in the rolling window
- **THEN** the response returns empty breakdown lists and zero counts without failing the capacity endpoint

### Requirement: Admin view compatibility

The admin dashboard and server-monitor view SHALL render the new monitoring summaries using the existing visual style and SHALL continue to render successfully when connected to an older backend that does not provide the additive breakdown fields.

#### Scenario: New backend breakdown is visible

- **WHEN** the capacity response includes request class and slow-route summaries
- **THEN** the dashboard displays a compact diagnostic section with class P95/error values and the slow-route list

#### Scenario: Server-monitor breakdown is visible
- **WHEN** an administrator opens the server-monitor view and the response includes request class and slow-route summaries
- **THEN** the server-monitor view displays the same compact diagnostic section below the resource cards

#### Scenario: Older backend remains usable

- **WHEN** the capacity response omits the new supporting breakdown object
- **THEN** the dashboard keeps existing cards and does not show an error
