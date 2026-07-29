## MODIFIED Requirements

### Requirement: Nginx MUST provide one standardized ingress role

The system MUST define Nginx as the standardized ingress for static resources, API proxying, compression, security headers, canonical-host redirects, and bounded SPA routing. Nginx MUST NOT carry business logic. It MUST serve the SPA document for known browser routes, preserve API forwarding, serve search-control resources in their standard formats, and return HTTP 404 for unknown paths.

#### Scenario: Browser requests a known web application route

- **WHEN** a user directly requests a browser route implemented by the React application
- **THEN** Nginx serves the Web entry document and the client router renders the existing product page

#### Scenario: Client requests an unknown route

- **WHEN** a client requests a path outside the known browser, API, static-resource, health, and SEO-resource routes
- **THEN** Nginx returns HTTP 404 rather than the homepage SPA shell

#### Scenario: API is called through the public domain

- **WHEN** a client accesses the API through the unified public domain
- **THEN** the reverse proxy preserves required request headers and identifiers and forwards the request to FastAPI
