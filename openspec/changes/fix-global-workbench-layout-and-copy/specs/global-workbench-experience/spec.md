## ADDED Requirements

### Requirement: Context-specific English workbench copy
The Global application SHALL render concise, context-specific English copy for the signed-in navigation, interview home, written-exam home, empty states, session summaries, and material-readiness summary. These surfaces MUST NOT expose Chinese source text or generic translation fallback prose.

#### Scenario: User opens the interview home
- **WHEN** an authenticated Global user opens the interview home with or without existing sessions
- **THEN** the heading, primary action, empty or active state, recent-session panel, and material summary SHALL use distinct English copy appropriate to their functions

#### Scenario: User navigates the workbench
- **WHEN** an authenticated Global user reads the desktop or mobile application navigation
- **THEN** every destination SHALL have a concise English label and an accessible name that describes the destination

#### Scenario: Empty Resume and Job Description libraries
- **WHEN** the visitor opens either empty library and its add-material dialog
- **THEN** headings, actions, field labels and placeholders SHALL be English without interpolated Chinese category names, while upload behavior and user-authored content remain unchanged

### Requirement: Responsive English workbench layout
The Global workbench SHALL preserve readable navigation, a clear content hierarchy, and usable primary actions across supported desktop, compact desktop, and mobile widths without clipping or letter-by-letter wrapping.

#### Scenario: User opens the workbench on a desktop display
- **WHEN** the viewport has enough room for the full navigation
- **THEN** the sidebar SHALL show complete English labels and the content SHALL present the primary action, current state, and supporting panels without overlapping or excessive empty space

#### Scenario: User opens the workbench at a compact width
- **WHEN** the viewport cannot fit the full sidebar and content comfortably
- **THEN** the application SHALL use the existing compact navigation pattern while keeping controls identifiable and content panels in a single readable column where needed

#### Scenario: User opens the workbench on mobile
- **WHEN** the viewport uses the mobile breakpoint
- **THEN** the sidebar SHALL be replaced by the existing bottom navigation and the page header action SHALL remain full-width and operable

### Requirement: Workbench presentation regression protection
The Global Web test suite SHALL detect reintroduction of generic fallback copy, Chinese source text, or missing primary navigation and actions on the workbench home surfaces.

#### Scenario: Global workbench tests run
- **WHEN** automated workbench presentation tests render the interview and written-exam home routes
- **THEN** the tests SHALL verify the expected English navigation and actions and SHALL fail if known generic fallback copy or Han characters appear in those scoped surfaces
