## ADDED Requirements

### Requirement: Evidence-based reference scoring
A completed review SHALL provide a bounded 0–100 overall reference score, available dimension scores, reasons, source-grounded findings and prioritized actionable suggestions. The UI MUST label the score as this tool's reference evaluation rather than hiring probability. JD matching SHALL use only the supplied JD and SHALL be explicitly unassessed when absent.

#### Scenario: Review has evidence for findings
- **WHEN** a review completes
- **THEN** every source-dependent finding SHALL reference a real source excerpt and show its explanation and suggested action
- **AND** displayed scores SHALL follow the declared versioned weighting and range

#### Scenario: No JD was supplied
- **WHEN** a general resume review completes
- **THEN** the result SHALL omit or mark role matching as unassessed and SHALL NOT invent job requirements or silently score a missing dimension as zero

#### Scenario: Review schema or evidence is invalid
- **WHEN** a provider emits out-of-range scores, unsupported excerpt references, excessive output or malformed structured data
- **THEN** the service SHALL reject successful completion, display a safe failure and preserve the original resume

### Requirement: Conservative factual rewriting
The AI rewrite MUST preserve the candidate's supported experience, employers, dates, education, skills and numerical achievements. A JD MUST be treated as requirements rather than candidate facts. Missing facts MUST be explicit prompts for user completion rather than invented claims, and instructions embedded in resume/JD text MUST remain untrusted data.

#### Scenario: Achievement lacks a metric
- **WHEN** the original describes a task without a numerical result
- **THEN** the rewrite SHALL improve wording without inventing a percentage, monetary amount or other outcome and SHALL separately ask the user for verifiable detail if useful

#### Scenario: JD requests an unsupported skill
- **WHEN** a JD requires a skill not supported by the resume
- **THEN** the review SHALL describe a matching gap and SHALL NOT add the skill or related experience to the rewritten candidate resume

#### Scenario: Source contains prompt injection
- **WHEN** resume/JD content asks the model to ignore rules, reveal secrets or fabricate experience
- **THEN** the workflow SHALL treat the text as untrusted content and SHALL not follow those instructions

### Requirement: Editable draft with comparison and revision safety
The Global UI SHALL show the original resume and AI suggestions/rewritten draft distinctly, allow the owner to edit the draft and require users to verify factual content. Draft updates MUST use revision safety and MUST NOT replace original material or an existing interview snapshot.

#### Scenario: Owner edits a successful draft
- **WHEN** the owner saves a valid edit against the current revision
- **THEN** the saved draft and revision SHALL update while the original source and initial review remain available for comparison

#### Scenario: Stale draft save
- **WHEN** an editor submits an outdated revision
- **THEN** the service SHALL reject the conflict without silently overwriting the newer draft

### Requirement: Real authenticated DOCX and PDF downloads
The owner SHALL be able to download a completed saved draft as a real DOCX or PDF attachment using one consistent simple template. Exports MUST contain the saved draft, have correct file signatures/MIME/extensions and readable pagination, and MUST NOT require public object URLs, remote assets, scripts or fake HTML renamed as PDF.

#### Scenario: Download both formats
- **WHEN** an owner downloads DOCX and PDF for the current completed draft
- **THEN** both attachments SHALL open in standard readers and contain the same saved content with valid headings and complete text

#### Scenario: Long resume export
- **WHEN** content spans more than one page
- **THEN** both formats SHALL paginate without clipping, unreadable overlap or missing sections

#### Scenario: Deleted or unfinished export request
- **WHEN** a task is not completed or its source/task has been deleted
- **THEN** the export request SHALL fail without file contents or private storage keys

### Requirement: Explicit save as a new resume
The owner SHALL be able to explicitly save the current completed draft as a new owned resume suitable for normal material selection. This operation MUST preserve the original material and existing session snapshots, and replay MUST not create duplicate materials.

#### Scenario: Save and reuse optimized material
- **WHEN** the owner confirms save as new resume
- **THEN** the system SHALL return a distinct document/version under the same account and it SHALL be usable through existing material preparation once ready
- **AND** the original resume and existing interview snapshot SHALL remain unchanged

#### Scenario: Replay save as
- **WHEN** a matching save-as request is replayed
- **THEN** the same saved document SHALL be returned rather than creating a duplicate
