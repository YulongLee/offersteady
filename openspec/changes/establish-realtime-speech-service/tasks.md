## 1. Realtime speech orchestration foundation

- [x] 1.1 Define Realtime Speech Service domain contracts, realtime connection lifecycle, and provider-agnostic ASR gateway interfaces
- [x] 1.2 Define session binding, authorized audio publishing, transcript revision, question detection, chat invocation, storage, and usage dependencies for one realtime speech flow
- [x] 1.3 Define structured realtime speech logs, degradation states, reconnect boundaries, and error classification rules

## 2. Transport, transcript, and question detection design

- [x] 2.1 Design realtime transport and control API contracts for audio publishing, transcript event delivery, answer state delivery, and reconnect recovery
- [x] 2.2 Design Qwen-first realtime ASR gateway and multi-provider replacement strategy without changing the public realtime speech contract
- [x] 2.3 Design revision-aware subtitle events, transcript persistence, and source-safe question detection outputs aligned with the approved prototype

## 3. Chat integration, storage, and verification

- [x] 3.1 Define Chat Service handoff, answer-task correlation, and session-scoped conversation storage for realtime speech-triggered answers
- [x] 3.2 Define usage attribution, privacy boundaries, raw-audio minimization, and downstream read boundaries for analytics or future billing
- [x] 3.3 Add AI and service verification tasks, including transcript quality, false-trigger prevention, degraded-mode behavior, and `openspec validate establish-realtime-speech-service --strict`
