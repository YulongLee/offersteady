## ADDED Requirements

### Requirement: Frontend runtime shall use Backend API as the only page data source
The Web product runtime SHALL load page data from Backend API responses and MUST NOT read `fixtureAdapter`, `syntheticState`, or equivalent synthetic page state as a runtime fallback.

#### Scenario: App startup loads backend state
- **WHEN** a user opens the Web app after authentication
- **THEN** the frontend SHALL request the required page state from Backend API
- **AND** the frontend MUST NOT initialize the product state from `syntheticState`

#### Scenario: Backend request fails
- **WHEN** a required Backend API request fails, times out, or returns an incompatible response
- **THEN** the page SHALL show a real loading error or supported empty state
- **AND** the page MUST NOT render fallback fixture data

### Requirement: Frontend runtime shall not expose fixture data source switching
The Web runtime SHALL remove fixture-vs-api switching from product configuration. Runtime configuration MAY still contain API base URL and environment labels, but MUST NOT offer a product data source mode that selects fixture state.

#### Scenario: Runtime config is read
- **WHEN** the frontend reads public runtime configuration
- **THEN** it SHALL resolve a Backend API base URL
- **AND** it MUST NOT select `fixture` as a product data source

#### Scenario: Legacy fixture environment variable is present
- **WHEN** a legacy `VITE_APP_DATA_SOURCE=fixture` value is present in the environment
- **THEN** the frontend SHALL ignore or reject that value for product runtime
- **AND** it MUST NOT instantiate the fixture adapter

### Requirement: Frontend product bundle shall not import fixture adapter
The production Web bundle SHALL NOT import the fixture adapter or synthetic state module through app entrypoints, route components, adapters, or runtime config.

#### Scenario: Product bundle is built
- **WHEN** the Web product bundle is built
- **THEN** product runtime modules SHALL NOT include imports from `fixture-adapter`
- **AND** any remaining fixture or builder code SHALL be limited to test-only modules

### Requirement: Page operations shall write through Backend API
User-visible mutations in the Web app SHALL call Backend API operations and MUST NOT update only local synthetic state.

#### Scenario: User creates or deletes an interview
- **WHEN** the user creates or deletes an interview from the Web app
- **THEN** the frontend SHALL call the corresponding Backend API
- **AND** the updated page state SHALL be derived from the API result or a follow-up API refresh

#### Scenario: User redeems points
- **WHEN** the user submits a points redemption code
- **THEN** the frontend SHALL call the Backend redemption API
- **AND** wallet balance and ledger entries SHALL reflect Backend API response data

#### Scenario: User deletes screenshot or cancels answer
- **WHEN** the user deletes a screenshot or cancels an answer
- **THEN** the frontend SHALL call Backend API operations for that action
- **AND** it MUST NOT simulate success by mutating fixture state only

### Requirement: Tests shall not depend on product fixture runtime
Frontend tests SHALL use API mocks, contract fixtures, or test-only builders instead of importing product fixture runtime as the app data source.

#### Scenario: UI regression test renders a page
- **WHEN** a UI regression test renders a page that needs app state
- **THEN** the test SHALL provide state via API mock responses or a test-only builder
- **AND** the test MUST NOT rely on product `fixtureAdapter` fallback behavior
