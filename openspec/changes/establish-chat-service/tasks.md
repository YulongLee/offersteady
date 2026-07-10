## 1. Chat orchestration foundation

- [x] 1.1 Define Chat Service domain contracts, answer-task lifecycle, and provider-agnostic LLM gateway interfaces
- [x] 1.2 Define session, retrieval, prompt, streaming, conversation-storage, and usage dependencies for one chat request
- [x] 1.3 Define structured chat logs, retry boundaries, and error classification rules

## 2. Prompt, model, and streaming design

- [x] 2.1 Design Chat API contracts for question submission, streaming answer delivery, and answer status reporting
- [x] 2.2 Design Prompt Builder, Prompt Template, and Prompt Config boundaries for session-aware interview answers
- [x] 2.3 Design Qwen-first LLM Gateway and multi-provider replacement strategy without changing the public Chat API

## 3. Conversation history, usage, and verification

- [x] 3.1 Define conversation history and conversation storage records aligned with Interview Session context
- [x] 3.2 Define token-usage attribution, usage persistence, and downstream read boundaries for billing and analytics
- [x] 3.3 Add AI evaluation and verification tasks, including `openspec validate establish-chat-service --strict`
