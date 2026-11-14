## ADDED Requirements

### Requirement: Tolerate an already disconnected control socket
The mock control endpoint SHALL tolerate RuntimeError and WebSocketDisconnect only at its final socket.close boundary after existing controller cleanup. It MUST NOT create a secondary unhandled disconnect traceback, change the public protocol or require a companion update.

#### Scenario: Final close reports peer disconnect
- **WHEN** the control receive loop ends and final socket.close raises WebSocketDisconnect
- **THEN** endpoint cleanup completes, its pump is cancelled and its controller is detached exactly once

#### Scenario: Final close is repeated or cancellation occurs
- **WHEN** close raises the existing RuntimeError or the endpoint is cancelled
- **THEN** the existing expected close exception is tolerated and cancellation is not swallowed

### Requirement: Preserve cleanup ownership and failure visibility
The change MUST preserve existing detach, pause, deadline, billing and old/new controller ownership behavior. Unexpected close or detach failures MUST remain visible. Synthetic tests MUST NOT use real accounts, production storage or model calls.

#### Scenario: An old control handler exits after replacement
- **WHEN** its old controller is already detached and a new controller owns the same session
- **THEN** the old handler's final cleanup does not remove, pause, close or bill the replacement controller

#### Scenario: Unexpected cleanup failure
- **WHEN** detach or close raises an unrelated exception
- **THEN** the error remains observable and is not suppressed as a normal disconnect

### Requirement: Deploy only the verified CN Backend increment
The authorized release SHALL derive from fresh actual1724/df78 with238 inputs and change only mock_interview.py, preserving237 original inputs,203 complete Schema,344 settings,44 dependencies, auxiliary format,d7 companion,366 Web files and seven non-targets. Every cutover and recovery MUST enforce all original seven work gates, CN entity gate, TCP8000 zero and ownership/single-writer proof. Private data MUST remain server-side.

#### Scenario: User work or uncertain state exists
- **WHEN** protected work or connections are nonzero or reads/identity/configuration cannot be verified
- **THEN** no service is switched or disconnected; known work is allowed to finish naturally and unknown/drift stops release

#### Scenario: Local tests and actual candidate probe pass
- **WHEN** all frozen source/contracts and idle guards pass
- **THEN** only CN Backend is switched and independently verified; actual startup errors and later observations are recorded before handoff, without Git publication
