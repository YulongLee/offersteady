## ADDED Requirements

### Requirement: One daily free creation for every active CN member
Every owner with any active CN time membership SHALL receive one free mock creation per Asia/Shanghai business date. Remaining quota SHALL refresh at local midnight. Credit purchases alone SHALL not grant membership. Quota consumption SHALL be atomic with successful creation, include deleted history, and respect original-date idempotency and trusted fault compensation.

#### Scenario: Active member creates and exhausts today's quota
- **WHEN** a day, week, month or administrator-granted active member creates today's first mock interview
- **THEN** creation costs zero points and remaining free quota is zero; subsequent creations require explicit 100-point confirmation

#### Scenario: Midnight and old request retry
- **WHEN** the business date crosses 00:00 Asia/Shanghai and the membership remains active
- **THEN** a new request can receive one free creation; retrying yesterday's request returns its original result without using today's quota

#### Scenario: Final quota is contested or history deleted
- **WHEN** concurrent requests claim the last free quota or a used history record is deleted
- **THEN** at most one creation consumes the quota; stale free quotes cannot silently charge points and deleting history does not restore quota

### Requirement: Fixed per-session points charge
A CN creation without free quota SHALL settle exactly 100 points once. CN interactions SHALL not incur minute, answer, TTS or report fees. Existing financial history SHALL remain intact; existing in-progress CN sessions SHALL not acquire new minute charges. Insufficient creation balance and creation failure SHALL leave no settled orphan fee. Only existing trusted terminal-fault compensation before a completed answer SHALL restore actual charges or quota once.

#### Scenario: Paid interaction pauses and reconnects
- **WHEN** a paid session uses multiple minutes, pauses, resumes, retries speech or generates its report
- **THEN** its new charges total 100 points for creation and no minute settlement or extra reservation occurs

#### Scenario: Failed, duplicated or refunded creation
- **WHEN** a creation cannot complete, is retried concurrently, or qualifies for trusted terminal-fault compensation
- **THEN** fee and quota changes remain atomic and idempotent; user cancellation after successful creation does not refund the entry charge

### Requirement: Server-enforced sixty-minute interview limit
CN mock sessions SHALL end interaction sixty minutes after their first successful start, using a persisted server deadline. Preparation SHALL not count. Pause, generation waits, disconnection, reconnect, browser refresh and process restart SHALL not reset or extend the deadline. At expiry the system SHALL stop capture/playback, fence unfinished question work, release binding and generate a full or partial report from confirmed answers, or an insufficient-evidence report without invented scores.

#### Scenario: Expiry in any active phase
- **WHEN** the fixed deadline is reached while listening, speaking, paused or generating a question
- **THEN** no further interaction or question publication is accepted and the server transitions to report/completion with a time-limit reason

#### Scenario: Offline session or process restart
- **WHEN** a previously started session reconnects or is recovered after its deadline
- **THEN** its original deadline is retained and expiry is completed; a new sixty-minute period is not granted

#### Scenario: A question result races expiry
- **WHEN** a question job finishes at or after the deadline
- **THEN** its result cannot revive interaction or add a question; report generation remains allowed

### Requirement: Clear CN pricing and independent existing flows
The CN UI SHALL show one daily free session for active members, 100 points per paid session, midnight reset and the sixty-minute limit. It SHALL refresh daily quotes and show authoritative session timing/end reasons. Normal interview, written-exam and Global practice pricing/eligibility SHALL remain unchanged. This change SHALL be developed and verified locally until separately authorized for deployment.

#### Scenario: Creation page survives midnight or changed pricing
- **WHEN** the page stays open across the business-date boundary, becomes visible again, or receives a stale-price error
- **THEN** it reloads the current server quote and offers an explicit paid confirmation when needed

#### Scenario: Another edition or feature is used
- **WHEN** an ordinary interview, written exam or Global practice session is created
- **THEN** its original policy applies, including Global's UTC daily-three quota and no access to the CN points wallet
