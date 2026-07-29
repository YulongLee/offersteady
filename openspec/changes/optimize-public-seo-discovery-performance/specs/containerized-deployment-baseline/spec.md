## MODIFIED Requirements

### Requirement: Nginx MUST provide one standardized ingress role

The system MUST define Nginx as the standardized ingress for static resources, API proxying, compression, security headers, canonical-host redirects, bounded SPA routing, route-specific index control, and immutable delivery of fingerprinted JavaScript and CSS assets. Nginx MUST NOT carry business logic.

#### Scenario: Browser requests a fingerprinted JavaScript or CSS asset

- **WHEN** a browser requests an existing Vite JavaScript or CSS asset whose filename includes its content hash
- **THEN** Nginx returns the asset with `Cache-Control: public, max-age=31536000, immutable` and preserves the established security headers

#### Scenario: Browser requests a fixed-name brand asset

- **WHEN** a browser requests a fixed-name logo, icon, or social sharing image
- **THEN** Nginx serves the file without incorrectly declaring it immutable

#### Scenario: Browser requests the Web entry document

- **WHEN** a browser requests the homepage or a known application route
- **THEN** the HTML response remains non-immutable so a deployment can reference newly fingerprinted assets immediately

#### Scenario: API is called through the public domain

- **WHEN** a client accesses the API through the unified public domain
- **THEN** reverse-proxy behavior and required request headers remain unchanged
