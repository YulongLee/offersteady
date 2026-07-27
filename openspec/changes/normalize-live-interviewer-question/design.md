## Context

Web 当前把候选人最后一次发言后的最多四段面试官 ASR 文本去重后以空格拼接，并将结果直接提交给 Live Answer。Chat Service 把同一字符串用于任务标题、快答、详细回答和 RAG，因此断句、口头语和跨片段指代会直接影响展示与回答质量。

快答已经采用两阶段流式生成：第一阶段快速输出简单回答，第二阶段检索知识库并补充详细回答。该链路对首字延迟敏感，不能为了问题整理再增加一次独立模型往返。

## Goals / Non-Goals

**Goals:**

- 在现有第一阶段模型调用内同时整理问题并生成简单回答。
- 保存原始问题和整理后的问题，保证可追溯。
- 让页面标题、简单回答、详细回答和 RAG 查询使用同一个整理后问题。
- 协议不符合预期或模型整理失败时安全回退原始问题。
- 保持回答正文继续流式输出。

**Non-Goals:**

- 不改变 ASR 分句和说话人识别。
- 不自动触发快答。
- 不修改截图回答链路。
- 不增加新的模型供应商或客户端密钥。
- 不修改现有实时面试页面布局。

## Decisions

### Decision 1: Reuse the quick-answer model call

快答 Prompt 要求模型先输出 `<normalized_question>...</normalized_question>`，随后输出 `<answer>...</answer>`。服务端增量解析这个短前缀，得到完整问题后再向页面发送回答正文。

选择该方案是因为它不增加模型请求，整理问题所需上下文已经存在于当前问题和最近会话历史中。

替代方案是单独调用轻量模型。该方案结构更清晰，但会增加网络、排队和模型首字耗时，不符合现场快答目标。

### Decision 2: Keep raw and normalized question separately

回答任务增加 `raw_question`、`normalized_question` 和 `question_normalization_status`。兼容字段 `question` 对外表示当前可展示、可回答的问题：整理成功后等于 `normalized_question`，失败时等于原始问题。

原始文本只用于追溯，不直接展示给用户，也不进入 RAG。

### Decision 3: Promote normalization through the existing task stream

不增加独立前端业务状态。模型前缀解析完成后，后端保存新版 task 并发送 `question-normalized` SSE 事件；现有前端 adapter 继续把 task 映射为 `InterviewQuestion`，因此页面顶部标题自然更新。

### Decision 4: Use normalized question for downstream stages

简单回答 Prompt 同时接收原始片段与最近会话上下文。解析完成后，详细回答 Prompt、知识库 embedding/rerank 和最终日志统一使用 `normalized_question`。手动输入仍可轻度整理，但不得改变用户明确输入的技术名词、数字或意图。

### Decision 5: Fail closed to the original question

标签缺失、为空、超长或格式异常时，后端把状态记为 `fallback`，使用清理后的原始问题继续回答。标签本身不得进入用户可见回答正文。

## Risks / Trade-offs

- [Risk] 模型不遵守标签协议 → 使用有界缓冲与原始问题回退，禁止标签泄漏到页面。
- [Risk] 为等待问题标签而延迟首个回答字 → 标签限制为一句话并与同一模型调用完成，不新增网络往返。
- [Risk] 模型改变问题原意 → Prompt 明确只允许去重、补全指代和恢复标点，并增加合成评测。
- [Risk] 老任务没有新字段 → API 字段提供兼容默认值，前端优先使用 `normalizedQuestion`，否则使用 `question`。
- [Risk] 原始转录增加敏感信息存储 → 仅保存在既有会话回答任务中，不保存原始音频，沿用会话删除策略。

## Migration Plan

1. 先发布兼容的新任务字段和 SSE 事件类型。
2. 更新 Prompt 与后端流式解析，让新任务开始产出整理问题。
3. 更新 Web adapter 和标题文案。
4. 验证历史任务仍能使用旧 `question` 字段展示。
5. 若线上模型标签遵循率异常，回滚 Prompt 和解析开关，任务继续使用原始问题。

## Open Questions

无。当前版本固定采用单次模型调用和原始问题安全回退。
