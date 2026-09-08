## ADDED Requirements

### Requirement: Chinese homepage presents the supplied product film
The Chinese public homepage SHALL include a clearly labelled product-film section that references a deployed static MP4 derivative and the supplied poster through website paths.

#### Scenario: Visitor opens the homepage
- **WHEN** the Chinese homepage renders
- **THEN** the product-film player displays the poster and references the static web MP4 without requiring authentication

### Requirement: Web derivative retains audio
The deployed MP4 SHALL contain one playable H.264 video stream and one AAC audio stream derived from the supplied master, and its duration SHALL remain materially equal to the master.

#### Scenario: Release asset is inspected
- **WHEN** the web MP4 is probed before deployment
- **THEN** both video and audio streams are present and the asset duration matches the source within normal transcode tolerance

### Requirement: Playback is user controlled and bandwidth conscious
The player SHALL have native controls, start muted, use inline playback and metadata-only preload, SHALL NOT autoplay, and SHALL allow the browser's native controls to enable sound and fullscreen where supported.

#### Scenario: Page loads before playback
- **WHEN** a visitor loads the homepage without interacting with the player
- **THEN** playback does not start, the player is muted, and the browser is instructed to preload metadata only

#### Scenario: Visitor chooses playback controls
- **WHEN** the visitor uses the native player controls
- **THEN** the visitor can start playback, enable sound and request fullscreen where the browser supports those controls

### Requirement: Player adapts to viewport size
The film container SHALL remain within the page width and preserve a 16:9 presentation on supported desktop and mobile viewports without horizontal overflow.

#### Scenario: Homepage renders on a narrow viewport
- **WHEN** the viewport is 720 CSS pixels wide or narrower
- **THEN** the player fits the available content width and retains its media aspect ratio
