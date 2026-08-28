## ADDED Requirements

### Requirement: English interview output SHALL remain English across every answer stage
For an authoritative `en-US` session, the system MUST generate the normalized question, quick answer, detailed answer, continuation, screenshot answer, and safe fallback in English. The output language MUST remain English when the question, session title, conversation history, screenshot text, resume, JD, or knowledge evidence is Chinese. Evidence facts SHALL remain unchanged and MUST NOT be persisted as translated source records.

#### Scenario: Chinese question appears in an English session
- **WHEN** an `en-US` interview submits the recognized question `介绍自己`
- **THEN** the displayed normalized question, quick answer, and detailed answer are English and no materially Chinese answer body is completed

#### Scenario: Chinese personal evidence supports an English answer
- **WHEN** an English session uses a Chinese resume or JD as untrusted evidence
- **THEN** verified facts may be expressed in English without inventing or changing candidate experience, while the generated answer remains English

#### Scenario: English screenshot contains mixed-language evidence
- **WHEN** an `en-US` screenshot task contains Chinese or mixed-language visible text
- **THEN** the generated quick and detailed answer sections remain English and distinguish visible facts from suggestions

### Requirement: English output language SHALL be enforced against provider drift
The backend MUST validate real provider output for `en-US` tasks instead of treating English prompt selection as proof of English output. A materially Chinese response MUST NOT be marked as a successful English answer. The system SHALL perform at most the configured bounded retry with an explicit English-repair directive and SHALL fail safely with a content-free error code if the provider continues returning the wrong language.

#### Scenario: First provider attempt drifts to Chinese
- **WHEN** the first English quick-answer attempt returns a materially Chinese normalized question or answer body
- **THEN** that attempt is not published, one bounded English-repair attempt is made, and only a compliant English result may complete the task

#### Scenario: Provider repeatedly returns Chinese
- **WHEN** every permitted provider attempt for an English answer is materially Chinese
- **THEN** the task ends in a recoverable failed state and does not expose the Chinese output as a successful answer

#### Scenario: Verified Chinese proper noun appears in English prose
- **WHEN** a long English answer contains a small verified Chinese proper noun while the surrounding answer is English
- **THEN** the guard does not reject the answer solely because a small number of Han characters are present

### Requirement: Chinese answer behavior SHALL remain unchanged
The new language contract, validation, repair retry, and English answer labels MUST activate only for authoritative `en-US` sessions. Existing `zh-CN` prompt assets, streaming behavior, answer text, and retry semantics SHALL remain unchanged.

#### Scenario: Chinese interview generates an answer
- **WHEN** a `zh-CN` session submits the same Chinese question and materials used by an English regression case
- **THEN** the system continues using the existing Chinese quick/detail pipeline without English enforcement or repair behavior

### Requirement: Answer language diagnostics SHALL not record user content
Language-enforcement telemetry SHALL record only the normalized session language, answer stage, prompt template identifier/version, attempt number, and stable violation/error code. It MUST NOT log the question, generated answer, transcript, screenshot, or personal-material text.

#### Scenario: English language guard rejects an answer
- **WHEN** a provider output violates the English language contract
- **THEN** operations can identify the session language, stage, attempt, and violation category without seeing any answer or evidence content
