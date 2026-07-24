## 1. Baseline and evaluation contract

- [x] 1.1 Add synthetic baseline cases for introduction, behavioral project, technical concept, system design, role fit, failure review, follow-up challenge and insufficient personal context.
- [x] 1.2 Add deterministic checks for direct opening, natural spoken body, section structure, quick/detail contradiction, excessive repetition, unsupported personal claims and JD-to-experience leakage.
- [x] 1.3 Add adversarial material cases proving Resume, JD and Knowledge prompt-injection text cannot override system policy.
- [x] 1.4 Record the current chat prompt and screenshot prompt baseline results, latency and output-length buckets without storing raw user content.

## 2. Versioned prompt components

- [x] 2.1 Create versioned live-answer shared policy, quick-answer and detailed-answer prompt components under `ai/prompts/chat-service/`.
- [x] 2.2 Encode adaptive strategies for common interview question intents with a safe general fallback and no extra model classification call.
- [x] 2.3 Encode authoritative-instruction and untrusted-evidence delimiters for question, conversation, Resume, JD and Knowledge sections.
- [x] 2.4 Create screenshot prompt v2 with code, algorithm, SQL, system design, multiple choice, debugging and unreadable-content strategies.
- [x] 2.5 Remove independent production answer-policy strings from backend runtime code and load all effective policy from versioned prompt files.

## 3. Shared live-answer context and consistency

- [x] 3.1 Implement a bounded internal answer context envelope containing the normalized question, recent confirmed conversation, fixed candidate facts, JD requirements, source availability and safe source identifiers.
- [x] 3.2 Reuse the same context envelope for quick and detailed stages and attach reranked Knowledge evidence only before the detailed stage.
- [x] 3.3 Pass the completed quick answer into the detailed prompt as an answer anchor that must be preserved, expanded and not mechanically repeated.
- [x] 3.4 Preserve backend-owned `简要回答`, separator and `详细回答` framing while streaming prompt-generated bodies.
- [x] 3.5 Record effective prompt template ID, version and strategy mode on answer tasks without recording rendered prompts or evidence text.

## 4. Grounding and source safety

- [x] 4.1 Separate candidate facts, JD requirements, Knowledge evidence, confirmed conversation and general technical knowledge in prompt assembly.
- [x] 4.2 Prevent JD requirements from becoming first-person candidate claims and prevent retrieved Knowledge from becoming unsupported project experience.
- [x] 4.3 Implement conservative conflict handling for inconsistent candidate facts and selected-but-unavailable sources.
- [x] 4.4 Add regression tests for Resume-only, JD-only, Knowledge-only, combined, conflicting, unavailable and no-context answers.

## 5. Screenshot answer quality

- [x] 5.1 Route screenshot response behavior by the visible problem type inside the single vision-model prompt.
- [x] 5.2 Require complete runnable code or SQL, relevant complexity or boundary explanation, and concise non-duplicative prose.
- [x] 5.3 Add conservative behavior for unreadable constraints, missing options, incomplete schemas and partially visible code.
- [x] 5.4 Add tests proving screenshot answers do not receive or claim use of Resume, JD or Knowledge context.
- [x] 5.5 Add synthetic screenshot evals for algorithm, SQL, system design, debugging, multiple choice and unreadable screenshots.

## 6. Prompt release governance

- [x] 6.1 Add privacy-safe prompt-version telemetry for source counts, input/output size buckets, first-token latency, completion latency, status and safe error code.
- [x] 6.2 Add a comparison command that reports candidate prompt results against the recorded production baseline.
- [x] 6.3 Gate prompt rollout on zero regression in fabrication, source isolation, privacy and complete code-answer checks.
- [x] 6.4 Add configuration for selecting chat v4 or the previous known-good chat prompt and screenshot v2 or the previous known-good screenshot prompt.
- [x] 6.5 Document staged rollout, production observation and configuration-only rollback procedures.

## 7. End-to-end verification

- [x] 7.1 Run backend unit and integration tests covering quick streaming, detailed RAG expansion, answer anchor consistency, cancellation and retry.
- [x] 7.2 Run the complete synthetic prompt eval suite and review failed cases before enabling new prompt versions.
- [x] 7.3 Compare first-token and completion latency with the current production baseline and remove prompt verbosity that causes material regression.
- [x] 7.4 Run one synthetic end-to-end interview with Resume, JD and Knowledge and verify answer quality, provenance and absence of unsupported facts.
- [x] 7.5 Run one synthetic screenshot code question and one unreadable screenshot case and verify completeness and conservative fallback.
