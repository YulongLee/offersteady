## MODIFIED Requirements

### Requirement: Separate user and telemetry quality

The admin capacity response SHALL classify `/api/v1/admin/*` requests as telemetry so management polling does not inflate user-facing API P95.

#### Scenario: Admin polling is excluded from user P95
- **WHEN** the admin UI polls dashboard, trend, payment, or server-monitor endpoints
- **THEN** those requests contribute only to telemetry summaries and slow-route diagnostics
