## ADDED Requirements
### Requirement: English usage tutorial
The Global homepage SHALL include the supplied narrated usage tutorial after workflow while retaining its product film and pricing.
#### Scenario: Visitor watches the tutorial
- **WHEN** the homepage renders
- **THEN** an English-labelled player exposes controls, muted inline playback and metadata preload without autoplay
- **AND** the original narration is available when the visitor unmutes
### Requirement: Isolated release
The tutorial SHALL use first-party range-capable media delivery and deploy only Global Web.
#### Scenario: Deployment verification
- **WHEN** the release is activated
- **THEN** video and poster requests succeed, byte ranges are supported and core services and China remain unchanged
