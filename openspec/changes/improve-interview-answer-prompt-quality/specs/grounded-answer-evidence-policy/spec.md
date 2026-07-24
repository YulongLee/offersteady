## ADDED Requirements

### Requirement: Answer evidence has explicit roles and priority
The system SHALL distinguish candidate facts, role requirements, retrieved Knowledge evidence, recent confirmed conversation and general knowledge. Resume facts and confirmed candidate statements MAY support first-person experience claims. JD requirements SHALL guide role matching but MUST NOT be converted into candidate experience. Retrieved Knowledge SHALL supplement only the question it matches.

#### Scenario: Resume and JD are both available
- **WHEN** a role-fit question is answered with confirmed Resume and JD context
- **THEN** the answer connects supported Resume capabilities to JD priorities without claiming that every JD requirement is already part of the candidate's experience

#### Scenario: Knowledge retrieval adds supporting detail
- **WHEN** reranked Knowledge evidence matches a technical question
- **THEN** the detailed answer may use that evidence while keeping personal project claims limited to confirmed candidate facts

### Requirement: Unsupported personal facts are prohibited
The system MUST NOT invent candidate companies, project names, responsibilities, team sizes, technical decisions, outcomes, metrics or dates. General technical explanation MUST remain distinguishable from candidate-specific experience.

#### Scenario: Personal metric is absent
- **WHEN** confirmed sources describe an optimization but contain no outcome metric
- **THEN** the answer may describe the supported optimization but MUST NOT add a percentage, latency value or business result

#### Scenario: No personal material is available
- **WHEN** the question asks for a personal project and the session has no usable Resume, JD-derived candidate fact or confirmed conversation fact
- **THEN** the answer MUST NOT fabricate a first-person project and SHALL state a concise limitation or provide a replaceable truthful structure

### Requirement: Conflicts and unavailable sources degrade safely
The system SHALL avoid silently selecting a convenient fact when confirmed sources conflict, and SHALL not claim to use a selected source that is unavailable, deleted or unreadable.

#### Scenario: Candidate facts conflict
- **WHEN** two confirmed sources contain conflicting values for the same candidate fact
- **THEN** the answer avoids the disputed value or identifies the uncertainty without inventing a resolution

#### Scenario: Selected Resume cannot be loaded
- **WHEN** the session selected a Resume but its processed artifact is unavailable
- **THEN** the answer remains conservative and its provenance reports that the Resume was not used

### Requirement: Evidence cannot override prompt policy
Resume, JD, Knowledge, transcript and screenshot text SHALL be treated as untrusted evidence. Instructions contained inside evidence MUST NOT override system policy, output structure, source boundaries or privacy requirements.

#### Scenario: Knowledge document contains prompt injection
- **WHEN** a retrieved chunk instructs the model to ignore prior rules or fabricate a stronger candidate result
- **THEN** the model ignores the instruction and uses only legitimate factual content that is relevant and supported
