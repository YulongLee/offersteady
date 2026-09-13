## ADDED Requirements

### Requirement: Global admin exposes only Live payment configuration
The international admin console SHALL display only the Creem Live configuration and SHALL NOT display a Test environment selector, Test credentials form, or Test activation control.

#### Scenario: Operator opens international payment settings
- **WHEN** an authenticated global operator opens the commerce settings
- **THEN** the page shows a single Live configuration with Live credentials, Live product mappings, and Live activation status

### Requirement: Global commerce rejects Test mode operations
The global commerce admin API SHALL reject requests that explicitly select `mode=test` without changing credentials, mappings, activation state, or customer data.

#### Scenario: Legacy client requests Test products
- **WHEN** a global admin client requests a Test product list or Test mapping
- **THEN** the API returns an unsupported/conflict response and records no Test mutation

### Requirement: Global checkout uses validated Live configuration
The global checkout and webhook paths SHALL use the validated Live provider configuration and SHALL remain unavailable until Live credentials, webhook secret, and all paid-plan mappings pass validation.

#### Scenario: Live configuration is incomplete
- **WHEN** a customer attempts checkout while any required Live configuration is missing or invalid
- **THEN** no provider checkout is created and the service returns a configuration-not-ready error

#### Scenario: Live configuration is ready
- **WHEN** the global master switch is enabled and all Live checks pass
- **THEN** checkout creation uses the Live Creem base URL and mapped Live product, and signed Live webhooks can reconcile the order idempotently

### Requirement: Domestic payments remain unchanged
The domestic edition SHALL retain its existing payment environments, providers, routes, and configuration behavior.

#### Scenario: Domestic admin opens payment settings
- **WHEN** an operator uses the domestic edition
- **THEN** domestic payment controls and behavior are unchanged by the global Live-only configuration
