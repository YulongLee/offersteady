## MODIFIED Requirements

### Requirement: Written exam entry costs 30 points once
The system SHALL apply the existing time-pass entitlement before charging written-exam entry. When a user has any currently valid time pass, entering a written session SHALL reserve and settle zero wallet points; when no valid time pass exists, entering a written session SHALL reserve and settle exactly 30 wallet points once. The entry charge MUST use a session-stable usage identifier and MUST remain separate from normal screenshot-answer charges.

#### Scenario: Written exam starts with an active one-day pass
- **WHEN** a preparing written session with a valid companion binding is started by a user with an active one-day time pass
- **THEN** the session enters the active state, the `written_exam_entry` usage is recorded as time-pass funded, and the wallet balance does not decrease

#### Scenario: Written exam starts with another active time pass
- **WHEN** a preparing written session with a valid companion binding is started by a user with any active time pass of at least one day
- **THEN** the session enters the active state without reserving or settling wallet points

#### Scenario: Written exam starts without a time pass
- **WHEN** a preparing written session with at least 30 available points and a valid companion binding starts successfully without an active time pass
- **THEN** the system settles one 30-point `written_exam_entry` usage and exposes the updated balance and auditable ledger entry

#### Scenario: Balance is insufficient for a points user
- **WHEN** a user without an active time pass has fewer than 30 available points after existing reservations
- **THEN** the system does not activate the written session and returns an insufficient-balance error without creating screenshot or audio work

#### Scenario: Start request is retried
- **WHEN** the same written session start command is repeated because of retry, refresh or timeout
- **THEN** the system returns the authoritative session and existing charge result without reserving or settling another entry charge, regardless of whether the original source was a time pass or wallet

#### Scenario: Activation fails after reservation
- **WHEN** written-session activation fails after a wallet reservation was created
- **THEN** the system releases the reservation and leaves the session preparing
