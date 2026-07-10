## ADDED Requirements

### Requirement: Backend shall provide authenticated page state for the Web app
Backend API SHALL provide all data required for the approved Web app pages under the authenticated internal User ID. The frontend MUST be able to render the existing UI without reading synthetic page state.

#### Scenario: Home page state is loaded
- **WHEN** an authenticated user opens the home page
- **THEN** Backend API SHALL provide the user's active interviews, resumable interview status, account summary, and any dashboard counters required by the existing UI
- **AND** the response SHALL be scoped to the authenticated internal User ID

#### Scenario: User information is loaded
- **WHEN** an authenticated user opens any page that displays account information
- **THEN** Backend API SHALL provide current user identity, display name, avatar when available, login provider, and account creation metadata

### Requirement: Material library state shall come from Backend API
The material library page SHALL render Resume, JD, and Knowledge Base data from Backend API responses, including upload status, processing status, deletion state, display names, versions, and supported file format guidance.

#### Scenario: Material library is opened
- **WHEN** an authenticated user opens the material library page
- **THEN** the frontend SHALL request Resume, JD, and Knowledge Base sources from Backend API
- **AND** the page SHALL display only sources owned by the authenticated internal User ID

#### Scenario: Material is created or deleted
- **WHEN** the user uploads or deletes Resume, JD, or Knowledge Base material
- **THEN** Backend API SHALL persist the operation
- **AND** the next page refresh SHALL show the updated Backend state

### Requirement: Interview history shall come from Backend API
Interview records, conversation history, screenshot history, answer history, and session lifecycle state SHALL be loaded from Backend API.

#### Scenario: Interview records page is opened
- **WHEN** an authenticated user opens interview records or history
- **THEN** Backend API SHALL provide the user's interview sessions, status, timestamps, conversation summaries, answer records, and screenshot records required by the existing UI

#### Scenario: Deleted interview no longer appears
- **WHEN** the user deletes an interview record and refreshes the page
- **THEN** Backend API SHALL no longer return that record for the user's history
- **AND** the frontend MUST NOT resurrect the record from local fixture state

### Requirement: Billing and points state shall come from Backend API
The billing page SHALL render wallet balance, points ledger, redemption results, pass status, pricing catalog, and points consumption explanation from Backend API.

#### Scenario: Billing page is opened
- **WHEN** an authenticated user opens the billing page
- **THEN** Backend API SHALL provide current wallet balance, ledger entries, active pass information, pricing catalog, and consumption rules required by the existing UI

#### Scenario: Points redemption succeeds
- **WHEN** the user redeems a valid code
- **THEN** Backend API SHALL return the new balance and ledger entry
- **AND** the frontend SHALL update the displayed billing state from that response

### Requirement: Screenshot state shall come from Backend API
Screenshot answer tasks, uploaded images, task status, generated answers, and history entries SHALL come from Backend API.

#### Scenario: Screenshot answer task is created
- **WHEN** the user submits one or more screenshots for answer generation
- **THEN** Backend API SHALL create the screenshot answer task
- **AND** the frontend SHALL display task status and answer content from Backend API or streaming API responses

#### Scenario: Screenshot history is loaded
- **WHEN** the user opens screenshot history or an interview containing screenshot answers
- **THEN** Backend API SHALL return screenshot records scoped to the authenticated internal User ID

### Requirement: API contract shall preserve the approved UI shape
Backend API responses and frontend adapter mapping SHALL preserve the approved Web UI structure and interaction order. Removing fixture state MUST NOT cause a redesign of routes, page layout, or component hierarchy.

#### Scenario: API contract replaces fixture state
- **WHEN** fixture data is removed from the product runtime
- **THEN** the frontend SHALL map Backend API responses into the existing domain model or an equivalent API-backed view model
- **AND** the visible UI structure SHALL remain consistent with the approved prototype
