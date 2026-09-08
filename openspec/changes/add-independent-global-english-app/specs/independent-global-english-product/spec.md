## ADDED Requirements

### Requirement: Independently buildable Global application
The system SHALL provide a Global end-user web application that can be installed, tested, built, configured, versioned, and deployed without changing the Chinese web application or the Chinese administration application.

#### Scenario: Build Global without modifying Chinese output
- **WHEN** an engineer builds the Global web application
- **THEN** the build SHALL use its own application entry, package identity, public configuration, and output directory
- **AND** the Chinese web build and administration build SHALL retain their existing entry points and defaults

#### Scenario: Keep production untouched during development
- **WHEN** the Global application is developed or tested locally
- **THEN** no Chinese production deployment, production secret, production database, or production domain SHALL be modified

### Requirement: English feature parity
The Global application SHALL expose English versions of the current end-user journeys, including public navigation, authentication, interview and written-exam preparation, materials, device pairing, realtime interview, quick answer, automatic answer, screenshot answer, programming preferences, review and export, billing presentation, settings, help, and legal pages.

#### Scenario: User navigates Global journeys
- **WHEN** a user opens any supported Global end-user route
- **THEN** user-facing navigation, headings, controls, validation, empty states, progress states, and failure guidance SHALL be presented in English

#### Scenario: Existing functionality is reused
- **WHEN** a Global user invokes a supported feature
- **THEN** the application SHALL preserve the corresponding Chinese product workflow and API contract except for explicitly isolated locale, branding, provider configuration, and deferred commercial integrations

### Requirement: English interview behavior
The Global application SHALL create interview sessions with English recognition and answer behavior by default and SHALL prevent user-facing AI answers from falling back to Chinese.

#### Scenario: Start a Global interview
- **WHEN** a Global user creates or starts an interview
- **THEN** the session language SHALL be `en-US` by default
- **AND** ASR hints, question detection, quick answers, detailed answers, continuations, screenshot answers, and programming answers SHALL use the English path

#### Scenario: Provider emits an incorrect output language
- **WHEN** an answer provider returns Chinese or mixed-language output for a Global session
- **THEN** the existing English-language validation and repair behavior SHALL run before the answer is accepted as complete

### Requirement: Regional English profiles
The Global application SHALL support `en-US`, `en-GB`, `en-AU`, and `en-CA` presentation profiles while retaining English as the product language.

#### Scenario: Select a regional profile
- **WHEN** the configured Global locale is one of the four supported profiles
- **THEN** the application SHALL use that profile for locale-sensitive formatting and regional product metadata
- **AND** SHALL continue to use the backend-supported English interview language contract

### Requirement: Global desktop companion presentation
The desktop companion SHALL provide an English Global build profile with an identity, labels, guidance, website target, update metadata, and release artifact that are isolated from the Chinese release profile.

#### Scenario: Build the Global companion
- **WHEN** an engineer builds the desktop companion with the Global profile
- **THEN** the artifact SHALL display English end-user text and use Global public endpoints supplied through that profile
- **AND** the packaged main process SHALL identify the Global edition from an immutable packaged marker rather than a runtime display name
- **AND** device registration, pairing identity, and user data SHALL remain isolated from the Chinese companion at runtime
- **AND** the existing Chinese companion profile and version channel SHALL remain unchanged

#### Scenario: Chinese companion copy changes
- **WHEN** a Chinese companion release adds or changes static or dynamic user-facing copy
- **THEN** the Global companion build SHALL require an explicit context-correct English translation before it can pass
- **AND** both editions SHALL continue to compile the same capture, pairing, recovery, shortcut, and update behavior

### Requirement: Chinese administration remains unchanged
The Global product work SHALL NOT translate, replace, or alter the normal behavior of the Chinese administration application.

#### Scenario: Operator opens administration
- **WHEN** an operator runs the existing administration application
- **THEN** the interface SHALL remain Chinese and SHALL retain its existing API behavior

### Requirement: Privacy and commercial deployment boundary
The Global application SHALL preserve data-minimisation and user-control boundaries and SHALL clearly separate locally complete product development from unresolved international infrastructure and commercial configuration.

#### Scenario: Product handles interview data
- **WHEN** Global users provide audio, screenshots, resumes, job descriptions, or knowledge materials
- **THEN** the product SHALL preserve the current non-persistence-by-default and user-control boundaries
- **AND** SHALL present English disclosure that users must follow applicable interview, recording, and AI-assistance rules

#### Scenario: International commercial services are not configured
- **WHEN** international server, domain, authentication, payment, legal approval, or provider credentials are unavailable
- **THEN** the repository SHALL remain locally buildable and testable
- **AND** SHALL NOT claim that international production deployment or commercial payment acceptance is complete
