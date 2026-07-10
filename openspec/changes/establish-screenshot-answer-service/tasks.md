## 1. Screenshot answer orchestration foundation

- [x] 1.1 Define Screenshot Answer Service domain contracts, screenshot-task lifecycle, and provider-agnostic vision gateway interfaces
- [x] 1.2 Define image upload registration, preprocessing, session, retrieval, prompt, streaming, history, and usage dependencies for one screenshot answer request
- [x] 1.3 Define structured screenshot-answer logs, retry boundaries, and error classification rules

## 2. Vision, prompt, and streaming design

- [x] 2.1 Design Screenshot Upload and Screenshot Chat API contracts for one or more ordered images
- [x] 2.2 Design image preprocessing, Qwen Vision gateway, and multi-provider replacement strategy without changing the public Screenshot Answer API
- [x] 2.3 Design prompt builder, prompt template, and streaming answer output for screenshot-grounded interview answers

## 3. History, usage, and verification

- [x] 3.1 Define screenshot answer history and session-scoped storage records aligned with Interview Session context
- [x] 3.2 Define usage attribution, usage persistence, and downstream read boundaries for billing and analytics
- [x] 3.3 Add AI evaluation and verification tasks, including `openspec validate establish-screenshot-answer-service --strict`
