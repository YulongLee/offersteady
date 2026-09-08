## ADDED Requirements

### Requirement: International homepage product film
The OfferSteady Global homepage SHALL present the supplied English product film in a clearly labelled section before the detailed workflow content.

#### Scenario: Visitor opens the homepage
- **WHEN** a visitor opens the OfferSteady Global homepage
- **THEN** the page contains an English heading, supporting copy, and a product-film player

### Requirement: User-controlled media playback
The product-film player MUST expose native controls, start muted, support inline playback, and preload metadata rather than the complete video.

#### Scenario: Homepage renders before playback
- **WHEN** the product-film player first renders
- **THEN** it has `controls`, `muted`, `playsinline`, and `preload="metadata"` behavior and does not autoplay

#### Scenario: Visitor chooses to hear or enlarge the film
- **WHEN** a visitor uses the native player controls
- **THEN** the visitor can enable the retained audio track and enter full-screen playback where the browser supports it

### Requirement: First-party media delivery
The Global Web service SHALL serve the product MP4 and poster from first-party `/media/` URLs with byte-range support suitable for browser playback.

#### Scenario: Browser requests the video
- **WHEN** a browser requests the configured MP4 URL or a byte range from it
- **THEN** the Global Web service returns the video asset with an appropriate media content type and range-capable response

### Requirement: Isolated Global Web release
Publishing the film MUST NOT change China-site behavior or restart Global core business services.

#### Scenario: Product film is deployed
- **WHEN** the new Global homepage release is activated
- **THEN** only the Global Web service is recreated and the Global Backend, Admin, workers, data services, and China production services remain unchanged
