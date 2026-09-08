## ADDED Requirements

### Requirement: Profile-scoped single Companion owner
The desktop Companion SHALL allow only one running application process to own polling, screenshot and capture loops for a product-edition profile.

#### Scenario: User launches the same Companion twice
- **WHEN** a second Companion process starts for the same domestic or Global profile
- **THEN** the existing Companion window SHALL be restored and focused, and the second process SHALL exit without starting network or capture loops

#### Scenario: Domestic and Global profiles coexist
- **WHEN** domestic and Global Companion applications are installed on the same computer
- **THEN** each edition SHALL retain its isolated profile and SHALL NOT block the other edition's primary process

### Requirement: Non-overlapping binding polling
The Companion SHALL have at most one binding-status request in flight and SHALL coalesce concurrent wakeups into one subsequent poll.

#### Scenario: Visibility changes during an in-flight binding request
- **WHEN** the Companion becomes visible while a binding request is still in flight
- **THEN** it SHALL complete the current request and schedule no more than one immediate follow-up request

### Requirement: Invalid screenshot binding suspension
The Companion SHALL distinguish a terminal missing or invalid screenshot binding from a transient transport failure and SHALL suspend screenshot stream and fallback polling for the terminal binding.

#### Scenario: Screenshot stream has no valid binding
- **WHEN** screenshot stream admission returns an explicit terminal no-binding response
- **THEN** the Companion SHALL stop retrying that stream and SHALL NOT issue a fallback screenshot task poll for the invalid binding

#### Scenario: Temporary network failure
- **WHEN** screenshot stream admission fails because of a network error or retryable server response
- **THEN** the Companion SHALL retain bounded exponential recovery without changing audio, transcript or answer behavior

### Requirement: Immediate wakeup for a new valid binding
The Companion SHALL resume screenshot delivery promptly when eligibility changes from suspended or idle to a new valid live binding.

#### Scenario: User starts a second interview after ending the first
- **WHEN** the renderer observes a new valid live binding after the previous screenshot binding was suspended
- **THEN** it SHALL wake exactly one main-process screenshot stream owner without waiting for the old failure backoff

