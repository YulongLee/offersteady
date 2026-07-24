## ADDED Requirements

### Requirement: Screenshot answers follow the detected problem type
The screenshot answer model SHALL identify the dominant visible problem type and apply an appropriate answer strategy for code or algorithm, SQL, system design, multiple choice, debugging, table or diagram analysis, and a safe general fallback. It MUST answer the visible problem directly and MUST NOT replace the solution with a generic framework.

#### Scenario: Algorithm problem is visible
- **WHEN** the screenshot contains a readable algorithm problem
- **THEN** the answer provides the core approach, complete runnable code in the requested or clearly inferred language, complexity and important edge cases

#### Scenario: SQL problem is visible
- **WHEN** the screenshot contains a readable SQL task and schema
- **THEN** the answer provides complete SQL and briefly explains joins, grouping, window behavior or null handling that materially affects correctness

#### Scenario: System design problem is visible
- **WHEN** the screenshot contains a system design prompt
- **THEN** the answer covers assumptions, architecture, data flow, storage, cache or queue choices, consistency, failure handling and scaling trade-offs relevant to that prompt

### Requirement: Screenshot answers preserve correctness over confident guessing
The model SHALL distinguish readable requirements from uncertain or missing screenshot content. It MUST NOT silently invent hidden constraints, sample input, schema fields or code that is not visible.

#### Scenario: Critical screenshot text is unreadable
- **WHEN** the model cannot reliably read information required for one definitive answer
- **THEN** it states the specific missing information, gives only a conditional best-effort answer when safe, and asks the user to verify or recapture the relevant content

#### Scenario: Multiple choice options are partially missing
- **WHEN** the question is visible but one or more answer options are not readable
- **THEN** the model explains the supported conclusion without claiming a definitive option letter

### Requirement: Screenshot answers remain isolated from personal materials
Screenshot answer generation SHALL use only the current confirmed screenshot and the user's screenshot instruction. It MUST NOT use Resume, JD, Knowledge RAG or inferred candidate experience.

#### Scenario: Session has selected materials
- **WHEN** a screenshot answer is requested during a session that has Resume, JD and Knowledge materials
- **THEN** the screenshot answer provenance reports no personal material use and the answer contains no claim derived from those materials

### Requirement: Screenshot output is concise but complete
The screenshot response SHALL preserve the existing `简要回答` and `详细回答` structure. The brief section SHALL state the result or core approach, and the detailed section SHALL include everything required to use or verify the solution. Explanation MUST remain concise when complete code or SQL already carries the implementation detail.

#### Scenario: Complete coding answer
- **WHEN** a coding problem requires an implementation
- **THEN** the detailed answer includes one coherent complete code block rather than fragmented pseudocode or an answer outline
