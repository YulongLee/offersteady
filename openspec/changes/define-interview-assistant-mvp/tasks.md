## 1. Product Decisions and Foundation

- [ ] 1.1 Resolve the open questions in `design.md` and record the approved MVP assumptions
- [ ] 1.2 Select the Web client, trusted API, persistence and test toolchain based on the approved assumptions
- [ ] 1.3 Scaffold the client and API applications with formatting, type checking, tests and build commands
- [ ] 1.4 Define shared types for source documents, processing states, interview sessions, normalized questions and answer suggestions
- [ ] 1.5 Add synthetic resume, JD, knowledge and question fixtures without real personal data

## 2. Resume Context

- [ ] 2.1 Implement resume upload validation for supported format and size limits
- [ ] 2.2 Implement server-side resume parsing behind a replaceable parser interface
- [ ] 2.3 Build the resume processing, review, correction and error states
- [ ] 2.4 Store only confirmed resume content and prevent unconfirmed fields from entering answer context
- [ ] 2.5 Implement resume replacement and deletion including derived retrieval data
- [ ] 2.6 Add unit and integration tests for upload, parsing failure, confirmation and deletion

## 3. Job Description Context

- [ ] 3.1 Implement JD text paste and supported file upload validation
- [ ] 3.2 Implement extraction of responsibilities, required skills, preferred skills and business context
- [ ] 3.3 Build the JD review, correction, insufficient-content and processing states
- [ ] 3.4 Implement JD replacement and cleanup of obsolete derived data
- [ ] 3.5 Add tests for text input, file input, incomplete JD and replacement

## 4. Interview Knowledge Base

- [ ] 4.1 Implement knowledge source creation from text and supported files
- [ ] 4.2 Implement chunking and indexing behind replaceable retrieval interfaces
- [ ] 4.3 Build source processing status, retry, disable, enable and delete interactions
- [ ] 4.4 Implement relevant-source retrieval with source identifiers and relevance filtering
- [ ] 4.5 Add tests for successful indexing, failed processing, disabled sources, deletion and no-result retrieval

## 5. Unified Answer Pipeline

- [ ] 5.1 Implement the normalized question model and question-type classifier
- [ ] 5.2 Implement context assembly across confirmed resume, JD and relevant knowledge fragments
- [ ] 5.3 Implement answer generation behind a replaceable model adapter with structured output validation
- [ ] 5.4 Prevent generated answers from presenting unsupported candidate experience as fact
- [ ] 5.5 Attach context-type and source metadata to each answer suggestion
- [ ] 5.6 Create AI eval cases for grounded answers, missing context, irrelevant retrieval and unsupported claims

## 6. Live Interview Workspace

- [ ] 6.1 Build the desktop-first workspace layout with document status, session controls and real-time answer area
- [ ] 6.2 Implement the preparing, ready, active, paused, ended and error session state machine
- [ ] 6.3 Implement start, pause, resume and end controls with explicit input authorization
- [ ] 6.4 Implement the approved real-time input method behind a replaceable input adapter
- [ ] 6.5 Add manual question input as the fallback path
- [ ] 6.6 Display question receipt, answer generation, completion, source and failure states
- [ ] 6.7 Implement retry and regeneration without losing the original question
- [ ] 6.8 Add integration and end-to-end tests for the complete live interview flow and failure recovery

## 7. Screenshot Question Assistance

- [ ] 7.1 Implement screenshot selection and paste input with type and size validation
- [ ] 7.2 Implement screenshot understanding behind a replaceable vision adapter
- [ ] 7.3 Build extracted-question preview, classification correction and ambiguous-image states
- [ ] 7.4 Implement structured response strategies for general written, coding and system-design questions
- [ ] 7.5 Implement default cleanup of original screenshots after request processing
- [ ] 7.6 Add tests for valid screenshots, invalid images, ambiguous content, each supported question type and cleanup

## 8. Privacy, Observability and Verification

- [ ] 8.1 Implement user-visible deletion for persisted resume, JD, knowledge and interview-session data
- [ ] 8.2 Redact source content, screenshots, prompts and credentials from application logs
- [ ] 8.3 Record parsing, retrieval and answer latency metrics without storing sensitive payloads
- [ ] 8.4 Run automated formatting, type, unit, integration, end-to-end and AI evaluation suites
- [ ] 8.5 Verify every scenario in the five capability specs and record evidence for failures or deferred items
- [ ] 8.6 Update `AGENTS.md` with the final verified install, test and build commands
