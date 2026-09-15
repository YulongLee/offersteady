## MODIFIED Requirements

### Requirement: Compatible WeChat authorization is non-production only

The development-compatible WeChat provider MUST NOT create authorization sessions, accept simulated scan/authorization actions, or complete its synthetic callback in a production environment. Development and test environments MUST retain the existing compatible flow for local and automated testing.

#### Scenario: Production rejects authorization session creation

- **GIVEN** the backend environment is `production`
- **WHEN** a caller posts to `/api/v1/auth/wechat/authorization-sessions`
- **THEN** the backend returns HTTP 404 with error code `wechat-production-disabled`
- **AND** no authorization session or user is created

#### Scenario: Development retains compatible authorization

- **GIVEN** the backend environment is `development` or `test`
- **WHEN** a caller creates a session and uses the existing compatible scan/authorize flow
- **THEN** the flow continues to return the existing waiting, scanned, and authorized states
