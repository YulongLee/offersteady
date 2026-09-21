## ADDED Requirements

### Requirement: Choose interview audio mode before preparation
The interview entry flow SHALL let the user choose between computer interview and mobile interview before entering the realtime preparation step, SHALL preselect computer interview, and SHALL persist the choice with the draft session.

#### Scenario: Computer interview is preselected
- **WHEN** a user opens realtime interview creation without a prior choice
- **THEN** computer interview is selected and described as the mode for interviews conducted on the Mac

#### Scenario: User selects mobile interview
- **WHEN** a user selects mobile interview and creates the draft
- **THEN** the preparation page loads that draft in mobile mode and shows the mobile-specific audio requirements

### Requirement: Preparation checks match the selected audio mode
The preparation page SHALL derive its audio-device instructions and readiness conditions from the persisted interview audio mode without changing the existing materials, language, programming, billing, or companion-pairing workflow.

#### Scenario: Computer preparation remains unchanged
- **WHEN** a computer-mode draft enters preparation
- **THEN** the existing system-audio and microphone preparation behavior remains available

#### Scenario: Mobile preparation omits system-audio requirement
- **WHEN** a mobile-mode draft enters preparation
- **THEN** the page requires the desktop companion and Mac microphone but does not require computer system audio before enabling start
