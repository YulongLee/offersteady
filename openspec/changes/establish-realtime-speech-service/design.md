## Context

当前 OfferSteady 的产品原型已经把“实时对话 + 实时回答”定义得比较清楚：左侧显示“我 / 面试官”的实时字幕，右侧显示 AI 回答，问题在足够明确时自动触发，也保留手动提问作为降级路径。与此同时，服务端已经有较成熟的 Session、Retrieval、Chat 和 Screenshot 边界，但实时语音链路仍然分散在桌面采集、说话人路由和未实现的音频任务之间，没有一个正式的 Realtime Speech Service 去把这些能力组织起来。

这次设计需要把下面几层串成一条正式主线：

- capture client（桌面伴随程序或后续浏览器采集端）
- realtime transport（WebSocket）
- ASR provider（Qwen Realtime ASR first）
- revision-aware transcript / subtitle events
- question detection
- Chat Service invocation
- answer streaming
- conversation storage / usage / logging

同时要遵守这些约束：

- 不改变你已经确认的前端原型交互
- Session 继续是权威会话上下文源
- Retrieval 与 Chat 继续保持独立边界
- provider key 仍然只保留在服务端
- 默认最小化保留原始音频
- 登录、支付、后台管理不纳入本次范围

## Goals / Non-Goals

**Goals:**

- 建立统一 Realtime Speech Service，负责实时语音辅助链路
- 提供会话绑定的 WebSocket 实时连接和低延迟音频接入
- 提供可替换的 Realtime ASR Gateway，第一版支持 Qwen Realtime ASR
- 输出可修订的实时字幕和转写片段，并与现有双角色原型一致
- 提供问题识别、Chat 调用、流式回答和会话级记录
- 记录 usage、日志和降级状态，并保持敏感数据最小暴露

**Non-Goals:**

- 不实现用户登录
- 不实现支付或计费策略
- 不实现后台管理
- 不在本次变更中重写 Chat Service、Retrieval Service 或桌面采集客户端
- 不把 provider-specific 参数、密钥或音频 SDK 暴露到客户端

## Decisions

### 1. Use Realtime Speech Service as the orchestration layer above capture, ASR, detection, and chat

Realtime Speech Service 作为独立编排层负责：

1. authenticate realtime publisher
2. bind connection to one interview session
3. receive ordered audio frames
4. call realtime ASR gateway
5. normalize transcript revisions
6. run question detection
7. invoke Chat Service
8. stream answer state to clients
9. persist transcript, question, answer references, and usage

原因：

- 现有能力分布在 capture、speaker routing、chat、session 多个模块之间，需要一个正式编排层把它们串起来
- 前端原型不应该自己拼 ASR、问题识别和回答调用
- 后续替换 provider、调优触发阈值或增加更多采集端时，变更范围可以控制在服务层内部

备选方案：

- 让桌面端或 Web 前端直接串 ASR 与 Chat：实现会更快，但会暴露敏感协议和 provider 细节，也难以统一会话记录

### 2. Keep realtime transport on a session-bound WebSocket contract

实时语音主链路采用会话绑定的 WebSocket，而不是把音频做成普通轮询上传。连接承担：

- publisher authorization
- session / source binding
- ordered frame delivery
- transcript / answer event fan-out
- reconnect and degradation signaling

原因：

- 原型要求低延迟字幕和回答更新
- WebSocket 更适合承载双向事件，而不仅是音频上传
- 能更自然地表达连接中断、降级和恢复状态

备选方案：

- HTTP chunk upload + polling：更简单，但时延和状态语义都更差

### 3. Isolate realtime transcription behind a provider-agnostic ASR gateway

第一版默认通过 Qwen Realtime ASR，但 Realtime Speech Service 只依赖抽象 ASR Gateway。Gateway 负责：

- audio request / response normalization
- transcript revision mapping
- provider-specific retry / timeout / error classification
- usage and latency extraction

原因：

- 你已经明确希望后续可切换模型路线
- 实时 ASR 的协议差异通常很大，需要在服务内部统一
- 便于用合成数据做服务测试，而不直接依赖厂商协议

备选方案：

- 在服务里直接耦合 Qwen Realtime API：前期快，但后续替换成本高

### 4. Model realtime subtitles as revisioned transcript events rather than append-only strings

字幕和转写不应只是不断 append 文本，而应建模为 revision-aware segment events，包含：

- segment id
- session id
- source id / source kind
- display role
- revision
- started / ended time range
- is_final / overlap / confidence state

原因：

- 原型已经要求只显示最新修订的字幕
- 问题识别必须基于最终或足够稳定的文本，而不是每个临时 token
- reconnect 和 history 恢复都需要稳定片段身份

备选方案：

- 只保留全文转写字符串：实现简单，但无法支撑修订、去重和问题边界判断

### 5. Keep question detection as a dedicated boundary between transcript and answer generation

问题识别不直接耦合在 ASR adapter 或 Chat Service 中，而是保留 dedicated detection boundary。它消费 transcript events，输出：

- no-op
- question candidate
- question confirmed
- degraded / manual confirmation needed

原因：

- 语音转写和“这是不是一个可回答问题”是两个不同问题
- 原型里“内容不清晰时确认问题”依赖这个边界
- 可以独立评测 false trigger、boundary precision 和 latency

备选方案：

- 让 Chat 直接吃每段转写：会导致误触发、重复调用和更高成本

### 6. Reuse Session + Retrieval + Chat boundaries rather than building a speech-specific answer stack

Realtime Speech Service 不自己实现 RAG 或 LLM 调用，而是：

- Session 提供权威会话上下文
- Retrieval 提供 Resume / JD / Knowledge 增强
- Chat Service 负责 Prompt、LLM、streaming answer、history 和 token usage

原因：

- 避免把相同回答逻辑重复写两次
- 让语音问题和手动问题最终进入同一回答事实源
- 与现有产品原型“同一个回答区域”保持一致

备选方案：

- 语音链路独立做一套 speech-chat service：边界更割裂，维护成本更高

### 7. Keep raw audio retention minimized and logs content-thin

服务只保留完成转写和问题识别所需的最小临时音频缓冲；普通日志只记录：

- request / connection id
- session id
- provider / model
- event type
- latency / retry / state
- transcript / answer identifiers
- error code

不记录：

- raw audio bytes
- provider secret
- full prompt
- 普通日志中的完整敏感音频内容

原因：

- 语音与面试内容高度敏感
- 需要满足产品边界中的最小化保存原则
- 仍然要保留足够的排障能力

备选方案：

- 在日志里保留完整转写和音频摘要：调试方便，但隐私风险过高

### 8. Treat degraded operation as a first-class state, not an exception path

Realtime Speech Service 明确定义这些服务状态：

- connected
- receiving-audio
- transcribing
- degraded
- reconnecting
- answer-streaming
- failed

原因：

- 原型已经有“自动回答暂停、可手动提问”的降级语义
- Realtime 场景里部分失败比完全失败更常见
- 明确状态有利于前端显示和后续测试

备选方案：

- 把降级都归为失败：实现简单，但用户体验与产品原型不一致

## Risks / Trade-offs

- [Risk] 实时语音链路跨越 capture、network、ASR、detection、chat 多层，延迟容易累积 → Mitigation: 通过 session-bound transport、revision events、bounded retries 和问题触发门限控制总时延
- [Risk] ASR 修订频繁会导致问题重复识别或字幕抖动 → Mitigation: 使用稳定 segment id、revision-aware 更新和 confirmed-question 去重机制
- [Risk] 候选人语音、回声或混合源可能误触发回答 → Mitigation: 保持 source-aware routing、question detection gate 和 manual-confirmation fallback
- [Risk] 实时音频和字幕内容敏感，日志或持久化容易过度留存 → Mitigation: 默认不长期保存原始音频，普通日志不记录 raw audio 和 provider secrets
- [Risk] Realtime Speech Service 与 Chat Service 都涉及流式状态，边界可能混淆 → Mitigation: Speech 只拥有 transcript / detection / orchestration，answer generation 仍归 Chat Service

## Migration Plan

1. 在 OpenSpec 中定义 Realtime Speech Service 的能力、状态和边界
2. 在 `apps/backend` 中建立会话绑定的 realtime transport、ASR gateway、transcript event normalization 和 detection orchestration
3. 通过既有 Session / Retrieval / Chat 边界接入回答生成，而不是新增 speech-only answer stack
4. 增加 session-scoped transcript / question / answer reference storage、usage 和结构化日志
5. 后续再通过独立变更接入更复杂的桌面端采集实现、取消控制和多端同步细节

回滚策略：

- 如果 realtime provider 适配存在问题，可回退为“仅连接状态 + 手动输入”的安全降级模式，不影响已有 Session / Chat / Screenshot 主链路
- 如果 question detection 质量不稳定，可关闭自动触发，仅保留实时字幕和手动确认问题路径

## Open Questions

- 第一版实时音频 publisher 是否只面向桌面伴随程序，还是同时支持浏览器麦克风直连？
- 第一版 transcript history 是否需要保存全部最终字幕，还是只保存确认问题附近的关键片段？
- answer cancellation 是否由 Realtime Speech Service 透传到 Chat Service，还是保持在后续独立变更？
- Qwen Realtime ASR 第一版采用官方 WebSocket 协议还是服务端包装后的统一 adapter？
