## ADDED Requirements

### Requirement: Answers adapt to the interview question
The system SHALL generate an answer that directly addresses the current confirmed question and adapts its organization to the question intent without adding a separate external model classification call. Supported intents MUST include introduction, project or behavioral experience, technical concept, system design, role fit, trade-off or failure review, follow-up challenge, and a safe general fallback.

#### Scenario: Behavioral experience question
- **WHEN** the interviewer asks for a challenging project experience
- **THEN** the answer presents a natural spoken narrative covering relevant context, the candidate's responsibility, key actions and supported outcome without exposing template field labels

#### Scenario: Technical concept question
- **WHEN** the interviewer asks for the difference between two technical concepts
- **THEN** the answer starts with the distinction and then explains decision criteria or a relevant example instead of forcing a personal STAR story

#### Scenario: Follow-up challenge
- **WHEN** the interviewer challenges a claim from the recent confirmed conversation
- **THEN** the answer responds to the challenge and preserves relevant established facts instead of repeating the original answer from the beginning

### Requirement: Quick and detailed answers remain consistent
The system SHALL present the existing `简要回答` and `详细回答` sections. The quick answer SHALL provide a direct, speakable opening, and the detailed answer SHALL preserve the quick answer's supported conclusion while expanding evidence, reasoning or trade-offs. The detailed answer MUST NOT mechanically repeat the entire quick answer or introduce unsupported contradictory claims.

#### Scenario: Quick answer appears before detailed expansion
- **WHEN** a live answer is generated with knowledge retrieval enabled
- **THEN** the quick answer can stream from the question and fixed context before retrieval completes and the detailed answer later expands the same core claim

#### Scenario: No relevant knowledge is retrieved
- **WHEN** no confirmed Knowledge chunk matches the question
- **THEN** the detailed answer expands only from the question, fixed context, recent confirmed conversation and general non-personal knowledge without claiming a Knowledge source was used

### Requirement: Answers are natural and ready to speak
Live interview answer bodies SHALL use concise, natural first-person Chinese suitable for speaking aloud. They MUST start with the answer rather than meta commentary, MUST avoid unnecessary headings and checklist language inside each section, and MUST avoid claiming that the candidate has performed actions not supported by confirmed evidence.

#### Scenario: Candidate asks for a role-fit answer
- **WHEN** the question asks why the candidate fits the role
- **THEN** the answer directly connects supported candidate capabilities to confirmed JD priorities in spoken language without saying `建议你这样回答` or listing an internal reasoning process

#### Scenario: Evidence is insufficient
- **WHEN** the question requires a personal example but no confirmed personal fact supports one
- **THEN** the answer provides a conservative truthful formulation and clearly leaves the unsupported detail for the user to replace with a real experience
