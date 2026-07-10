## ADDED Requirements

### Requirement: All supported uploaded documents MUST be parsed through one unified parser service
The system SHALL route Resume, JD, and Knowledge Base documents that enter the processing pipeline to one shared Document Parser Service rather than embedding format-specific parsing logic directly in the pipeline scheduler.

#### Scenario: Shared parser entrypoint across document types
- **WHEN** a Resume, JD, or Knowledge Base document reaches the parsing stage
- **THEN** the system MUST invoke the same Document Parser Service entrypoint with document metadata and storage location

#### Scenario: Pipeline remains a scheduler
- **WHEN** the processing pipeline dispatches a parsing task
- **THEN** the pipeline MUST only coordinate task scheduling, stage progression, and retries rather than directly implementing document parsing rules

### Requirement: The parser service MUST support the approved upload formats
The system SHALL support parsing documents in PDF, DOCX, DOC, TXT, and Markdown formats and MUST reject unsupported or unreadable formats with a safe parser error result.

#### Scenario: Binary document parsing
- **WHEN** the input document format is PDF, DOCX, or DOC
- **THEN** the parser service MUST process the file through the configured parser provider path for binary office-style documents

#### Scenario: Plain text document parsing
- **WHEN** the input document format is TXT or Markdown
- **THEN** the parser service MUST process the file through a plain text parsing path and still return normalized Markdown output

#### Scenario: Unsupported or invalid format
- **WHEN** the parser service receives a document whose format is unsupported, corrupted, or inconsistent with its declared type
- **THEN** the parser service MUST return a parser failure result with a machine-readable error code and retryability flag

### Requirement: The parser service MUST output normalized Markdown
The system SHALL convert all successfully parsed documents into one normalized Markdown representation so that downstream chunking and embedding consume a single text format.

#### Scenario: Successful parse returns normalized markdown
- **WHEN** a document is parsed successfully
- **THEN** the parser service MUST return Markdown content that has passed a normalization step rather than raw provider output

#### Scenario: Downstream stages do not branch by original file type
- **WHEN** chunking or embedding consumes parser output
- **THEN** those downstream stages MUST receive a unified Markdown text payload instead of needing to inspect the original file format

### Requirement: The parser service MUST update parsing-stage processing status
The system SHALL allow the parser service to report parsing-stage status transitions and parsing outcomes without taking ownership of non-parsing pipeline stages.

#### Scenario: Parsing starts
- **WHEN** the parser service begins reading and parsing a document
- **THEN** the system MUST record that the processing task has entered the parsing stage

#### Scenario: Parsing succeeds
- **WHEN** the parser service completes successfully
- **THEN** the system MUST record parsing success metadata so that the task can continue into downstream chunking and embedding stages

#### Scenario: Parsing fails
- **WHEN** the parser service cannot parse a document
- **THEN** the system MUST record a parsing failure status, error code, and retryability signal without incorrectly advancing the task into later stages

### Requirement: The parser service MUST classify parser failures for retry handling
The system SHALL distinguish recoverable parser failures from permanent parser failures so that the processing pipeline can make consistent retry decisions.

#### Scenario: Recoverable parser failure
- **WHEN** the parser service encounters a temporary provider, network, timeout, or object retrieval failure
- **THEN** it MUST return a failure classification that marks the error as retryable

#### Scenario: Permanent parser failure
- **WHEN** the parser service encounters a corrupted file, empty document, unsupported structure, or unrecoverable format problem
- **THEN** it MUST return a failure classification that marks the error as non-retryable

### Requirement: The parser service MUST produce structured logs without raw document content
The system SHALL emit structured parser logs and task events that are useful for operations while excluding raw resumes, JD text, knowledge base body text, or full Markdown output from ordinary logs.

#### Scenario: Parser observability
- **WHEN** the parser service starts, succeeds, or fails for a document
- **THEN** the system MUST log structured metadata such as task id, document id, file kind, provider name, duration, retry count, and error code

#### Scenario: Sensitive content is excluded from logs
- **WHEN** parser logs or task events are recorded
- **THEN** they MUST NOT include raw file bodies, full parsed Markdown, chunk text, or embedding vectors
