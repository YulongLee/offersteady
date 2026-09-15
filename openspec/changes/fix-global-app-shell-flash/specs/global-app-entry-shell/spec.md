## ADDED Requirements

### Requirement: Workspace routes use an application entry shell

When the browser loads `/app` or any nested `/app/...` route before React mounts, the document MUST display a workspace-oriented loading shell and MUST NOT display the public marketing prerender as the primary content.

#### Scenario: Direct navigation to workspace

- **WHEN** a user opens `/app` with JavaScript still loading
- **THEN** the page shows a neutral workspace loading state
- **AND** the marketing hero, pricing, and public navigation are hidden for that route

#### Scenario: Nested workspace route

- **WHEN** a user opens an `/app/...` route directly
- **THEN** the same application entry shell is used before React mounts

### Requirement: Public routes preserve the existing prerender

The route-aware shell MUST NOT alter the existing marketing prerender on `/` or public content routes.

#### Scenario: Public landing route

- **WHEN** a user opens `/`
- **THEN** the current marketing prerender remains visible before React mounts
- **AND** its indexable headings and navigation remain present in the HTML

### Requirement: React bootstrapping clears the entry shell

After the React application mounts, the temporary application-entry marker and fallback shell MUST be removed or hidden so that the existing React loading, login, or workspace screen is the only visible application content.

#### Scenario: React becomes ready

- **WHEN** the module entry point mounts the React tree
- **THEN** the temporary app-entry shell no longer obscures the React UI

### Requirement: No service contract changes

This capability MUST NOT change authentication, API requests, interview sessions, or persisted user data.

#### Scenario: Existing workspace behavior

- **WHEN** the shell is used on a workspace route
- **THEN** the existing authentication and state-loading flow proceeds unchanged
