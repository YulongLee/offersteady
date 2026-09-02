## ADDED Requirements

### Requirement: Public homepage displays official social accounts
The public homepage SHALL display an official Douyin account and an official Xiaohongshu account in its contact area. Both account values MUST be “面试稳AI助手”, and the existing customer-service WeChat, email and service hours MUST remain available.

#### Scenario: Visitor reviews homepage contacts
- **WHEN** a visitor reaches the public homepage contact area
- **THEN** the page displays “抖音号” and “小红书号”
- **AND** each account value is “面试稳AI助手”
- **AND** the existing WeChat, email and service-hours contacts remain visible

### Requirement: Live interview provides non-disruptive social contacts
The live interview page SHALL provide an on-demand contact entry that exposes the same Douyin and Xiaohongshu account values without replacing, delaying or changing interview controls, audio capture, transcription or answer behavior.

#### Scenario: Desktop user opens contacts during an interview
- **WHEN** a desktop user opens the contact entry on the live interview page
- **THEN** the page displays the Douyin and Xiaohongshu accounts as “面试稳AI助手”
- **AND** the live conversation and answer workspace remains available

#### Scenario: Mobile user opens more interview actions
- **WHEN** a mobile user opens the existing more-actions menu on the live interview page
- **THEN** the menu includes the Douyin and Xiaohongshu accounts as “面试稳AI助手”

### Requirement: Social contact values remain consistent
The homepage and live interview page MUST render their Douyin and Xiaohongshu account labels and values from one shared Web presentation source.

#### Scenario: Social account copy is rendered in both locations
- **WHEN** both the homepage contact area and live interview contact entry are rendered
- **THEN** their platform labels and account values are identical
