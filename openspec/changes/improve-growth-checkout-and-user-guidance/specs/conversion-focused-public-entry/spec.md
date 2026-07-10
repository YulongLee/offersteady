## ADDED Requirements

### Requirement: Hero communicates the interview outcome directly
The public hero SHALL use a positive, user-facing value proposition similar to “AI 面试助手，助你更从容地冲刺 Offer”. It SHALL explain real-time question assistance, personal context and supported input modes without making an employment guarantee.

#### Scenario: Visitor opens the public homepage
- **WHEN** a visitor views the first screen
- **THEN** the visitor can identify the interview-assistance outcome, primary capabilities and next action without interpreting internal architecture or negative positioning statements

### Requirement: Free use is the primary entry action
The primary public CTA SHALL be labelled “免费使用” or equivalent user-facing language and SHALL display the one-time 200-point new-user grant nearby. Public UI MUST NOT use “进入产品原型” outside a development-only diagnostic surface.

#### Scenario: New visitor evaluates signup cost
- **WHEN** the visitor reviews the primary CTA
- **THEN** the page states that the user can begin with 200 points without paying first

### Requirement: Flexible pricing is visible before signup
The homepage SHALL explain that users can choose point-based usage or 3/7/15/30-day membership according to their interview schedule. Any displayed price MUST come from the published server catalog.

#### Scenario: Visitor compares usage rhythms
- **WHEN** the visitor opens the pricing-value section
- **THEN** the page distinguishes occasional point usage from short-term high-frequency membership and links to complete pricing terms

### Requirement: Trust boundaries remain discoverable but secondary
The interface SHALL keep AI-advice, truthful-experience, privacy and platform-capability boundaries available in a trust section without using them as the primary hero proposition.

#### Scenario: Visitor checks product boundaries
- **WHEN** the visitor opens the trust or privacy section
- **THEN** the page explains that outputs are suggestions, personal experience must remain truthful and data controls are available

### Requirement: Closing section emphasizes direct product value
The closing public value section SHALL lead with question understanding, personalized answer structure and flexible usage. Trust boundaries SHALL remain concise secondary copy with a link to full guidance rather than a dominant `CLEAR BOUNDARIES` card.

#### Scenario: Visitor reaches the closing section
- **WHEN** a visitor scrolls beyond the pricing summary
- **THEN** the page presents three direct user benefits before the secondary AI-advice and privacy statement
