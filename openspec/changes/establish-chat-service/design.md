## Context

当前 OfferSteady 已经具备统一的 Document Processing、Embedding Pipeline、Knowledge Retrieval Service 和 Interview Session Service。也就是说，“资料进入系统”“文档可被检索”“会话拥有权威上下文”这些基础已经建立起来了，但还缺少真正把这些输入汇总成 AI 面试回答的生成层。

当前原型中的实时回答区域已经定义了清晰的用户体验：问题进入后，系统需要尽快给出增量回答，支持多轮上下文，并与会话、资料和后续用量统计保持一致。要满足这个目标，Chat Service 必须补齐以下缺口：

- 统一的 Chat API 和回答任务边界
- Prompt Builder 与 Prompt Template 管理
- 可替换的 LLM Gateway
- Streaming Response 输出
- Conversation Storage 与会话级历史记录
- Token Usage 统计、结构化日志和错误重试

与此同时，本次设计仍要遵守几个约束：

- 不改变前端原型结构和实时问答交互语义
- Retrieval 继续是独立服务，只返回上下文，不直接拼 Prompt
- Session 继续是权威上下文源，Chat 只消费 Session
- Screenshot 与 Speech 继续保持在本次范围之外

## Goals / Non-Goals

**Goals:**

- 建立统一 Chat Service，负责实时问答生成链路
- 接入 Interview Session 和 Knowledge Retrieval Service，支持多轮上下文和资料增强
- 提供 Prompt Builder、Prompt Template 和 Prompt 配置边界
- 提供可替换的 LLM Gateway，第一版支持 Qwen Chat API
- 支持 Streaming Response、Conversation Storage、Token Usage、日志和重试
- 保持前端原型交互不变

**Non-Goals:**

- 不实现 Screenshot Pipeline
- 不实现 Speech Capture / ASR
- 不在本次变更中改变 Retrieval Service 边界
- 不把底层 provider-specific 参数直接暴露给前端

## Decisions

### 1. Use Chat Service as the orchestration layer above Session and Retrieval

Chat Service 负责组织完整生成链路：

1. receive question
2. load session
3. call retrieval
4. build prompt
5. call LLM gateway
6. stream output
7. store conversation
8. record token usage

原因：

- Session 已经负责权威会话状态，Retrieval 已经负责知识上下文，最自然的下一层就是 Chat orchestration
- 让前端只对一个 Chat API 说话，而不是自己串多个依赖
- 能把日志、重试和状态管理集中在生成服务内部

备选方案：

- 让前端分别调用 retrieval 和 model API 再拼接：实现快，但会把敏感逻辑和 provider 细节暴露到客户端

### 2. Keep prompt construction behind Prompt Builder + Prompt Template boundaries

Chat Service 不直接在 handler 里拼 prompt，而是拆成：

- Prompt Builder：负责把 question、session、retrieval context、history 组织成模型输入
- Prompt Template：负责 system prompt、role structure、style / policy 文案版本
- Prompt Config：负责引用哪套 template / version / strategy

原因：

- Prompt 很快会变成高频迭代资产
- 便于把 Prompt 版本与评测集、线上效果和 token 成本对齐
- 避免把 prompt 逻辑散落在 API / service / provider adapter 中

备选方案：

- 直接在 Chat Service 里硬编码 prompt 字符串：实现最简单，但后续维护成本高

### 3. Keep LLM invocation behind a provider-agnostic gateway

第一版默认通过 Qwen Chat API 生成回答，但 Chat Service 只依赖抽象的 LLM Gateway。Gateway 负责：

- request / response normalization
- streaming adapter
- provider-specific retries / error mapping
- usage extraction

原因：

- 你已经明确希望后续支持切换不同 LLM
- 让 Chat orchestration 与 provider SDK 或 HTTP 协议解耦
- 有利于测试和后续多模型实验

备选方案：

- 直接在 Chat Service 中耦合 Qwen SDK：交付更快，但替换模型时改动面更大

### 4. Treat streaming as answer-task state, not just transport bytes

Streaming 不只是一串文本分片，而应建模为 answer-task 生命周期，例如：

- `queued`
- `streaming`
- `completed`
- `failed`
- `cancelled`

流式输出不仅返回 chunks，还要有 clear completion / failure signal，并与会话历史和后续“终止回答”能力兼容。

原因：

- 原型要求实时回答区知道回答是否完成、失败或被中断
- 后续终止回答、重试和用量结算都依赖任务状态，而不是裸流
- 比单纯把 provider stream 透传给前端更稳

备选方案：

- 只透传 provider token 流：前期简单，但状态一致性差

### 5. Store conversation as session-scoped answer history with structured records

Chat Service 不应只把“最终大段答案文本”塞进数据库，而要与 Session Conversation Context 对齐，保存：

- user question entry
- assistant answer entry
- answer task metadata
- prompt / retrieval references
- status and timing

原因：

- 与已有 Session Service 的 conversation context 设计保持一致
- 有利于恢复历史、调试、复盘和后续评价
- 便于在失败或重试时保留真实状态而不是只保留成功结果

备选方案：

- 只保存最后答案字符串：对后续可观测、重试和多轮上下文都不够

### 6. Attribute usage through Chat Service into Session usage records

Chat Service 负责从 provider usage 或估算器中提取 token 数据，然后写回 Session usage records。Billing 或 analytics 后续再读取这些事实数据。

原因：

- Chat 是最接近 usage 真相的地方
- Session 已经是统一的 usage 归属边界
- 避免 provider-specific usage 结构直接泄漏到业务层

备选方案：

- 只在 billing 里统计：容易与真实生成链路脱节

### 7. Keep retry logic at the gateway/orchestration boundary with idempotent answer records

重试不应该由前端决定，而应由 Chat Service + Gateway 在服务端统一执行。重试需要满足：

- answer task idempotency
- retryable vs non-retryable error classification
- no duplicate successful answer records
- clear failure state after retries exhausted

原因：

- 前端不应背负 provider 异常语义
- 可以避免重复写入聊天记录、重复计费或重复完成事件
- 与后续 Streaming / Cancel / Billing 能更自然协作

备选方案：

- 前端自行重试：实现简单，但状态与存储一致性更差

### 8. Keep logs structured and content-minimized

Chat 日志记录：

- request id
- session id
- answer task id
- provider / model
- prompt version
- stream mode
- latency
- token counters
- retry count
- final status / error code

不记录：

- full prompt
- full answer body
- full retrieval context
- large private document excerpts

原因：

- 资料和回答内容都可能高度敏感
- 仍然需要足够的排障能力
- 与 Retrieval / Session 的最小暴露原则一致

备选方案：

- 记录完整 prompt / answer：调试方便，但隐私风险太高

## Risks / Trade-offs

- [Risk] 流式任务状态比单次同步返回更复杂 → Mitigation: 将 streaming 建模为 answer-task 生命周期，并保持 API 契约清晰
- [Risk] Retrieval、Session、Prompt、LLM 四层串联后时延上升 → Mitigation: 通过超时、上下文裁剪、TopK 配置和 provider 重试预算控制总耗时
- [Risk] Prompt 版本快速迭代可能导致效果不稳定 → Mitigation: 把 Prompt Template 与 Prompt Config 独立并要求补充 `ai/evals/`
- [Risk] Provider streaming 语义差异会放大适配成本 → Mitigation: 用 LLM Gateway 统一标准化 chunk / completion / error / usage 结构
- [Risk] 聊天记录与 Session Context 重复存储 → Mitigation: 使用 session-scoped structured history，并明确 answer-task metadata 与 plain conversation entry 的关系

## Migration Plan

1. 在 OpenSpec 中定义 Chat Service 能力边界、Prompt / Gateway / Streaming / Storage / Usage 规则
2. 在 `apps/backend` 中建立 Chat API、Prompt Builder、LLM Gateway 和会话级 conversation storage
3. 让 Chat Service 调用 Interview Session Service 和 Knowledge Retrieval Service，而不是直接依赖底层文档或向量层
4. 将 usage、日志和 answer-task 状态统一接入会话边界
5. 后续再通过独立变更接入 Screenshot、Speech 和更复杂的取消/中断策略

回滚策略：

- 若 provider 或 streaming 适配有问题，可先保留同步非流式 fallback，不影响 Session / Retrieval 已有边界
- 若 Prompt / Gateway 实现存在问题，可限制回滚范围在 Chat 模块内部，而不回退 Session 与 Retrieval

## Open Questions

- 第一版是否需要把“终止回答”一起纳入 Chat Service，还是在后续独立变更接入？
- Conversation Storage 第一版是否保存完整答案正文，还是保存摘要 + 原始 answer artifact 引用？
- 是否需要在第一版就支持多套 prompt strategy，例如“简洁回答”和“STAR 回答”？
- Qwen provider 第一版是否采用官方 SDK、HTTP API，还是保持更薄的自定义 HTTP adapter？
