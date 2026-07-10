## ADDED Requirements

### Requirement: Core product resources SHALL bind to one internal User ID
The system SHALL bind Resume, JD, Knowledge Base, Interview Session, Conversation, Screenshot, Speech, and History records to one internal OfferSteady User ID rather than to provider-native identity data.

#### Scenario: Newly created business resources are owned by the authenticated user
- **WHEN** an authenticated user creates or uploads a Resume, JD, Knowledge document, Interview Session, Screenshot task, Speech session, or related history record
- **THEN** the created resource SHALL persist the authenticated internal User ID as its owner

#### Scenario: Provider identity does not replace the internal owner key
- **WHEN** business modules persist or query user-owned resources after WeChat login
- **THEN** those modules SHALL use the internal User ID as the ownership key and SHALL NOT use raw provider subject values as the business-layer owner identifier

### Requirement: Protected APIs SHALL resolve authenticated user identity through shared authentication middleware
The system SHALL require protected APIs to resolve the current user through shared authentication middleware or dependency boundaries rather than through feature-local token parsing.

#### Scenario: Protected request includes valid access token
- **WHEN** a client calls a protected API with a valid authenticated access token
- **THEN** the API layer SHALL resolve the authenticated internal User ID and make that identity available to the feature module through a shared authentication boundary

#### Scenario: Protected request lacks valid authentication
- **WHEN** a client calls a protected API with no token, an expired token, or a revoked session context
- **THEN** the system SHALL reject access and SHALL NOT return or mutate user-owned resources

### Requirement: Cross-user resource access SHALL be isolated
The system SHALL prevent one authenticated user from reading, modifying, or deleting another user’s owned resources across core product modules.

#### Scenario: User requests a resource owned by someone else
- **WHEN** an authenticated user requests a Resume, JD, Knowledge item, Interview Session, Conversation, Screenshot, Speech record, or History entry that belongs to a different internal User ID
- **THEN** the system SHALL deny that operation and SHALL NOT expose the other user’s resource payload

#### Scenario: User queries their own business data after WeChat login
- **WHEN** a user completes WeChat login successfully and then requests their own materials, sessions, or history
- **THEN** the system SHALL return only the resources owned by that authenticated internal User ID

### Requirement: User profile responses SHALL expose safe identity data only
The system SHALL expose only safe internal user profile fields to product clients and SHALL avoid exposing provider secrets or unnecessary provider identity data.

#### Scenario: Product client loads authenticated profile summary
- **WHEN** the client requests the authenticated user profile after login
- **THEN** the response SHALL include User ID, nickname, avatar, login provider, created time, and last login time

#### Scenario: Sensitive provider credentials remain server-side
- **WHEN** the login flow completes or the client refreshes its authenticated session
- **THEN** the system SHALL NOT expose provider secrets, provider access tokens, refresh secrets, or raw callback credentials to the product client
