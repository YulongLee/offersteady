## ADDED Requirements

### Requirement: Transient live recovery remains invisible to the interview user
During an active interview, the Web application SHALL keep transient transport and source recovery internal and MUST NOT render reconnect wording, a global reconnect warning, recovery explanation, or manual retry action solely because the runtime reports `reconnecting`, `preparing`, or temporarily stale signal freshness. Recovery state SHALL remain available to operational diagnostics, while the user-facing live presentation remains in its active interview state.

#### Scenario: Healthy capture is silent
- **WHEN** desktop capture remains reported as active but no fresh audio signal is observed during a period of silence
- **THEN** the live page remains in its normal non-alarming capture presentation and does not show a reconnect warning

#### Scenario: Established transport recovers automatically
- **WHEN** a previously healthy desktop transport or source enters an automatically recoverable reconnect state
- **THEN** the recovery continues in the background while the user-facing live presentation remains active and contains no reconnect wording, alert, or retry button

### Requirement: Actionable capture failures remain visible
The Web application SHALL continue to expose capture failures that require user action, including missing permission and unrecoverable device errors, with an appropriate action or diagnostic path.

#### Scenario: Permission is required
- **WHEN** the authoritative capture state reports that a required desktop permission is unavailable
- **THEN** the live page shows the existing actionable permission notice

#### Scenario: Device capture fails unrecoverably
- **WHEN** the authoritative capture state reports an unrecoverable device error
- **THEN** the live page shows the existing device-error notice and diagnostic action
