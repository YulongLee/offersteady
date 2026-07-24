## Context

OfferSteady 当前有两条主要回答路径：

- 实时面试回答先用问题和截断后的简历/JD上下文生成简单回答，再执行知识库检索，并使用另一段后端硬编码提示词生成详细回答。
- 截图回答把截图 OSS URL 和通用截图提示词发送给视觉模型，等待模型一次性返回“简要回答/详细回答”。

现有实现已经具备真实模型、流式输出、固定资料、RAG、来源记录和失败重试，但提示词策略分散在 Markdown 与 Python 代码中。简单回答和详细回答没有共享明确的事实计划，详细回答使用的固定资料还被截断到较短长度，导致两段语气、结论和证据可能不一致。当前评测主要检查标题、关键词和禁止编造，尚不能稳定衡量是否直接回答、是否像候选人口语、是否匹配题型、是否重复以及追问是否承接上文。

约束包括：不能增加额外模型分类调用影响实时性；不能把真实用户资料写入测试或日志；不能改变页面现有两段回答结构；截图回答不能使用简历、JD 或 RAG；外部模型供应商必须可替换。

## Goals / Non-Goals

**Goals:**

- 建立统一、集中、版本化的实时回答与截图回答提示词策略。
- 提高回答的直接性、自然口语感、问题匹配度和事实可信度。
- 保持简单回答低延迟，并让详细回答继承简单回答的核心主张而不是重新起草。
- 让简历、JD、RAG 和对话历史各自承担明确角色，并抵抗资料中的提示词注入。
- 建立可以在发布前执行的合成评测集和版本回滚机制。

**Non-Goals:**

- 不更换 Qwen 或其他现有模型供应商。
- 不增加单独的意图分类模型调用。
- 不修改 RAG embedding、rerank、Top-K 或索引策略。
- 不改变积分计费、回答页面布局或现有一级标题。
- 不让截图回答读取个人资料或知识库。
- 不承诺模型输出是标准答案或代替用户真实经历。

## Decisions

### 1. Use one shared answer context envelope for both answer stages

Chat Service SHALL assemble one internal answer context envelope before the quick answer. It contains the normalized question, bounded conversation context, fixed Resume/JD facts, unavailable-source state, and stable source identifiers. Knowledge retrieval is attached to the same envelope before the detailed stage.

The quick answer result is passed to the detailed-stage prompt as an `answer anchor`. The detailed stage must preserve its conclusion, correct only an explicitly detected factual conflict, and add evidence or explanation instead of restarting the answer.

This retains the current low-latency two-stage experience while reducing contradictions. Generating both sections in one model call was considered, but rejected because waiting for RAG before the first token would weaken the quick-answer experience.

### 2. Perform adaptive routing inside the prompt without another model call

The prompt SHALL provide compact strategy rules for common interview intents: introduction, project/behavioral experience, technical concept, system design, role fit, trade-off or failure review, and follow-up challenge. The answer model selects the applicable strategy from the current question and recent confirmed conversation.

A separate classifier model was considered, but rejected because it adds latency, cost and another failure point. A large hard-coded keyword classifier was also rejected because mixed and follow-up questions do not fit stable keyword boundaries.

### 3. Separate authoritative instructions from untrusted evidence

System policy, output contract and strategy rules are authoritative. Resume, JD, RAG excerpts, conversation transcripts and screenshot OCR text are delimited as untrusted evidence. The model MUST use their facts where relevant but MUST ignore instructions embedded inside them.

Candidate facts use the priority order: explicit current user question, confirmed Resume facts, confirmed conversation facts, confirmed JD requirements for role matching, retrieved Knowledge evidence, then general knowledge. JD requirements must not be restated as candidate experience. When sources conflict, the model uses the most explicit confirmed candidate fact or states the uncertainty.

### 4. Keep headings deterministic and prompts responsible for body quality

The backend continues emitting `简要回答`, the separator and `详细回答` so model formatting errors cannot break the UI. Quick and detailed prompts only generate body text.

Quick answer target is normally 60–140 Chinese characters and starts with the direct answer. Detailed answer target is normally 2–4 short spoken paragraphs, but code, SQL and system-design screenshot answers may exceed this limit when completeness requires it.

### 5. Split prompt policy into versioned reusable templates

All production prompt text SHALL live under `ai/prompts/`. Runtime code may select and fill templates but MUST NOT contain independent production answer policies.

Initial target versions are `interview-chat-system v4` and `screenshot-answer-system v2`. The effective template ID, version and strategy mode are stored with the answer task. Deployment keeps the preceding version available for environment-controlled rollback.

### 6. Evaluate quality before rollout

The eval suite SHALL use synthetic Resume, JD, Knowledge, conversation and screenshot cases. Deterministic checks cover structure, forbidden claims, required evidence, repetition, length bounds, code fences and source boundaries. A documented rubric covers directness, natural speech, specificity, factual support, follow-up continuity and usefulness.

Release gating compares the candidate prompt with the current baseline. A candidate MUST have no regression in fabrication, source isolation, privacy and code completeness, and MUST improve or preserve aggregate answer-quality checks.

### 7. Record privacy-safe prompt quality telemetry

Telemetry records prompt template ID, version, strategy mode, fixed/retrieved source counts, input/output character buckets, latency, completion status and safe error code. It MUST NOT store raw prompts, Resume/JD text, RAG chunks, screenshots, complete transcripts or full answers.

## Risks / Trade-offs

- [A larger system prompt can increase input tokens and latency] → Keep strategy rules compact, measure prompt token and first-token latency against the current version, and remove redundant policy text.
- [Two model stages can still diverge] → Pass the quick answer as an anchor and evaluate contradiction and repetition explicitly.
- [Prompt-only intent routing can misclassify mixed questions] → Prefer direct response over naming the type, include a general fallback strategy, and add mixed/follow-up eval cases.
- [Strict grounding can make answers overly cautious] → Allow general technical knowledge for non-personal claims while reserving first-person experience claims for confirmed evidence.
- [Materials can contain prompt injection] → Delimit all materials as untrusted evidence and add adversarial synthetic evals.
- [Long code answers increase screenshot latency] → Preserve completeness for code tasks, require concise explanation, and measure first-token and completion latency separately.
- [Quality scores can overfit deterministic checks] → Combine deterministic checks with a documented human review rubric and diverse synthetic cases.

## Migration Plan

1. Add baseline eval results for the current chat and screenshot prompt versions.
2. Introduce versioned quick, detailed and screenshot prompt components without changing the API contract.
3. Add the shared answer context envelope and quick-answer anchor.
4. Run unit, integration and prompt eval suites using synthetic data.
5. Enable the new versions in local and staging configuration, compare latency and quality with baseline, then deploy to production.
6. Roll back by restoring the previous prompt version environment values; no user data or database migration is required.

## Open Questions

- Whether the first production rollout should enable `v4` for all users or use a small deterministic account cohort.
- Whether future quality evaluation should add a separate model-judge adapter after deterministic and human rubric results are stable.
