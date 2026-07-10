## ADDED Requirements

### Requirement: WeChat action opens an official authorization experience
Clicking the WeChat login action SHALL create a short-lived server authorization session and open an official WeChat QR dialog, popup or supported in-WeChat OAuth redirect. Production UI MUST NOT simulate a successful provider callback.

#### Scenario: Desktop user starts WeChat login
- **WHEN** the user clicks “微信登录” in a desktop browser
- **THEN** the page opens an accessible login dialog or popup with official authorization state, expiry and close controls

#### Scenario: Popup is blocked
- **WHEN** the browser blocks the official authorization popup
- **THEN** the page falls back to a same-page QR or same-window authorization path without treating the user as authenticated

### Requirement: Authorization completes login, registration or binding safely
After validated provider authorization, the system SHALL log in an existing binding, create an account for an unbound identity or bind it to the reauthenticated current account. Identity collision MUST enter verified recovery and MUST NOT silently merge accounts.

#### Scenario: New WeChat identity authorizes successfully
- **WHEN** a valid callback is received for an unbound identity
- **THEN** one OfferSteady account and binding are created and the login window returns a safe authenticated result

#### Scenario: Binding belongs to another account
- **WHEN** the current user attempts to bind an identity already owned elsewhere
- **THEN** both accounts remain unchanged and the user receives a recovery path

### Requirement: Login dialog exposes complete recoverable states
The dialog SHALL represent loading, waiting-for-scan, authorized, expired, closed, provider-failure and callback-failure states without exposing codes, tokens or provider subject identifiers.

#### Scenario: Authorization QR expires
- **WHEN** the authorization session reaches its expiry
- **THEN** the dialog disables the expired QR and offers a server-generated refresh action

### Requirement: Development identity is isolated from production
Local prototype login MAY exist only behind an explicit development flag and SHALL not be rendered in production builds.

#### Scenario: Production login page loads
- **WHEN** the deployment environment is production
- **THEN** the page does not show or accept a local prototype identity

