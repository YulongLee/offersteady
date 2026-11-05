## ADDED Requirements

### Requirement: Content free acknowledgement uses lightweight authority
CN performance acknowledgements SHALL preserve route/fields/stages, owner verification, original cache lifetime and denial semantics while using the optional authoritative control projection without reading bound documents. Non-CN and unsupported repositories SHALL retain their prior path.

#### Scenario: All stages and foreign owner
- **WHEN** each supported stage sends synthetic timing fields or a foreign/missing session is used
- **THEN** accepted trace fields and original errors remain, the original owner/cache boundary is honored and no bound document is loaded on the projection path

#### Scenario: Disabled debug logging
- **WHEN** logging is INFO and acknowledgements arrive repeatedly
- **THEN** telemetry is still accepted and recorded without constructing unused DEBUG JSON or changing subtitle/heartbeat frequency
