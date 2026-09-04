## ADDED Requirements

### Requirement: Profile-scoped single Companion owner
The desktop Companion SHALL allow only one running application process to own polling, screenshot and capture loops for a product-edition profile.

#### Scenario: User launches the same Companion twice
- **WHEN** a second Companion process starts for the same profile
- **THEN** the existing window SHALL be restored and focused, and the second process SHALL exit before starting runtime loops

### Requirement: Non-overlapping binding polling
The Companion SHALL have at most one binding-status request in flight and SHALL coalesce concurrent wakeups into one subsequent poll.

#### Scenario: Visibility changes during an in-flight request
- **WHEN** the Companion becomes visible while a binding request is in flight
- **THEN** it SHALL complete that request and schedule no more than one immediate follow-up

### Requirement: Invalid screenshot binding suspension
The Companion SHALL suspend screenshot stream and fallback polling for an explicit terminal missing binding while preserving retryable recovery.

#### Scenario: Screenshot stream has no valid binding
- **WHEN** admission returns an explicit terminal no-binding response
- **THEN** retries and fallback task polling SHALL stop for that binding

#### Scenario: Temporary network failure
- **WHEN** admission fails due to a network error or retryable server response
- **THEN** bounded recovery SHALL continue without changing core behavior

### Requirement: Immediate wakeup for a new valid binding
The Companion SHALL resume screenshot delivery promptly after eligibility changes to a new valid live binding.

#### Scenario: A second interview starts
- **WHEN** a new valid binding follows a suspended binding
- **THEN** exactly one main-process screenshot owner SHALL wake without waiting for the old backoff
