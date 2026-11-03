## ADDED Requirements

### Requirement: Target image incremental release
The release SHALL derive from the actual Global fixed image and complete source inventory and SHALL preserve configuration, dependencies, schema, Web, helper, worker, CN and all non-target components.

#### Scenario: Source or contract drift
- **WHEN** any frozen source/image/config/controller/contract or non-target signature differs or cannot be read
- **THEN** automatic switching stops without bypassing protection

### Requirement: Protected idle single writer switch
The release SHALL repeat all seven existing Global read-only user gates, entity-state gates, strict zero TCP and ownership/single-writer checks before prepare/preflight/switch/recovery. Existing work SHALL finish naturally.

#### Scenario: Busy or unknown state
- **WHEN** any interview/task/connection is active or a read is unknown
- **THEN** the original service remains and no user work is ended, cleared or disconnected

#### Scenario: Verified candidate or repeated invocation
- **WHEN** the fixed candidate is healthy and independently verified or deployment is invoked again
- **THEN** actual attribution and output are checked and an already deployed owned candidate is not restarted

### Requirement: Honest private evidence
The release SHALL retain production private configuration and raw user logs on server and report bounded aggregate acceptance/errors without fabricated performance gains or real provider/load tests.

#### Scenario: Post release acceptance
- **WHEN** independent verification and short natural traffic observation complete
- **THEN** exact contract preservation, real startup failures and observation limits are saved before reporting completion
