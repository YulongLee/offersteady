## ADDED Requirements

### Requirement: Global operator navigation is edition-specific
The Global Admin SHALL expose only dashboard, server health, users, Global Creem commerce, materials, interview sessions, audit records, and administrator access modules.

#### Scenario: Global administrator opens the console
- **WHEN** the Admin bundle is built for the Global edition
- **THEN** its navigation contains exactly the approved Global operational modules

### Requirement: China-only commercial modules are absent from Global Admin
The Global Admin MUST NOT expose the domestic promotion centre, domestic order and payment diagnostics, WeChat or Alipay settings, referral growth settings, points catalogue, or redemption-code modules.

#### Scenario: Global navigation is rendered
- **WHEN** a Global administrator has permissions that would otherwise allow China-only modules
- **THEN** none of the China-only module entries is rendered or selectable

### Requirement: Chinese Admin remains unchanged
The Chinese Admin SHALL retain its existing promotion, domestic billing, payment-channel, growth, catalogue, and redemption operations.

#### Scenario: Chinese Admin is built
- **WHEN** the Admin bundle is built without the Global product-edition selector
- **THEN** the existing Chinese module identifiers remain present

### Requirement: Edition-specific fallback remains valid
The Admin SHALL choose a visible permitted view from the active edition list when the requested view is unavailable.

#### Scenario: Removed Global view is unavailable
- **WHEN** Global Admin resolves a China-only view or a view lacking permission
- **THEN** it falls back to the first permitted Global view without requesting the removed module API
