## ADDED Requirements

### Requirement: Hero communicates the interview outcome directly
The public hero SHALL use a positive, user-facing value proposition similar to “AI 面试助手，助你更从容地冲刺 Offer”. It SHALL explain real-time question assistance, personal context and supported input modes without making an employment guarantee.

#### Scenario: Visitor opens the public homepage
- **WHEN** a visitor views the first screen
- **THEN** the visitor can identify the interview-assistance outcome, primary capabilities and next action without interpreting internal architecture or negative positioning statements

### Requirement: Free use is the primary entry action
The primary public CTA SHALL be labelled “免费使用” or equivalent user-facing language. The hero SHALL provide an adjacent “使用手册” action that opens the guide directly without requiring sign-in. The hero MUST NOT display a points amount or use “看看怎么收费” as an action. Public UI MUST NOT use “进入产品原型” outside a development-only diagnostic surface.

#### Scenario: New visitor chooses the next action
- **WHEN** the visitor reviews the primary CTA
- **THEN** the visitor can either start free use or open the user guide directly
- **AND** no points amount or “看看怎么收费” link appears in the hero

### Requirement: Flexible pricing is visible before signup
The homepage SHALL explain that users can choose point-based usage or 3/7/15/30-day membership according to their interview schedule. Any displayed price MUST come from the published server catalog.

#### Scenario: Visitor compares usage rhythms
- **WHEN** the visitor opens the pricing-value section
- **THEN** the page distinguishes occasional point usage from short-term high-frequency membership and links to complete pricing terms

### Requirement: Common interview platforms are presented with truthful compatibility boundaries
The homepage SHALL present a responsive compatibility section for common remote-interview, collaboration and online-assessment platforms using the current homepage theme surfaces and card hierarchy. Each platform SHALL use a traceable authentic brand mark alongside a visible recognizable name, preserve the mark's proportions and colors, and MUST NOT substitute initials, a fabricated logo or an unexplained symbol-only mark. The section SHALL explain that OfferSteady uses user-authorized system audio, microphone and screenshot capabilities, and MUST NOT claim universal compatibility, official partnership or direct platform integration without verified evidence.

#### Scenario: Visitor checks whether their interview platform is covered
- **WHEN** the visitor views the platform compatibility section
- **THEN** the page presents Zoom, Google Meet, Microsoft Teams, 腾讯会议, 飞书, 钉钉, 企业微信, 力扣, 牛客 and Slack as common usage scenarios
- **AND** each platform uses a real brand mark from a recorded source rather than a generated abbreviation
- **AND** the page discloses that actual availability depends on system permissions, platform audio settings and the current release

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

### Requirement: Commercial footer provides product, documentation and configured contact access
The public homepage SHALL end with a responsive multi-column footer containing brand positioning, links to current product sections, publicly accessible guide and legal documents, configured customer-service WeChat ID and email, and the required filing link. Contact values MUST come from the public server support configuration rather than duplicated component constants.

#### Scenario: Visitor looks for help or contact information
- **WHEN** the visitor reaches the homepage footer
- **THEN** the visitor can open the public guide, installation guidance, user agreement and privacy policy
- **AND** the footer displays the currently configured customer-service WeChat ID, email and service hours
- **AND** the MIIT filing number links to the official filing website
