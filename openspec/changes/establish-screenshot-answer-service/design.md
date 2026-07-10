## Context

当前 OfferSteady 已经有文档上传、统一检索、会话管理和实时文字问答的基础工程，前端原型也已经明确了“截图回答”在实时工作台中的入口与流程：用户在当前会话内选择或拍摄图片，预览后提交，然后等待系统返回回答。现在缺少的是服务端正式的 Screenshot Answer Service，把图片处理、视觉理解、检索增强、Prompt 拼接、流式回答和历史记录统一起来。

这条链路与纯文字 Chat Service 相似，但又有三个明显不同点：

- 输入首先是图片，不是文本问题，因此需要 upload / preprocess / vision 理解
- 一次任务可能包含多张截图，需要保留图像顺序与组合语义
- 日志和存储要更严格避免泄露图片正文、题目截图或图像内容

与此同时，本次设计仍需满足这些约束：

- 不改变你已确认的前端原型交互
- 继续以 Interview Session 为权威上下文
- 继续以 Retrieval Service 提供资料增强
- Speech / ASR 不纳入本次实现范围

## Goals / Non-Goals

**Goals:**

- 建立统一 Screenshot Answer Service，负责截图型问答链路
- 支持图片上传、图片预处理、视觉模型调用、Prompt Builder、Streaming Answer 和历史记录
- 支持一场任务内多张截图
- 支持 Resume、JD、Knowledge 自动增强
- 让截图回答与 Session、Retrieval、Chat 风格的 usage / history / logging 边界保持一致
- 保持产品原型交互不变

**Non-Goals:**

- 不实现 Speech Capture / ASR
- 不在本次变更中改造 Chat Service 的主契约
- 不把视觉模型提供方的 SDK 或参数直接暴露给前端
- 不改变原型中的截图发起、预览和提交路径

## Decisions

### 1. Use Screenshot Answer Service as a sibling orchestration layer to Chat Service

Screenshot Answer Service 与 Chat Service 共享很多模式，但不直接塞进同一个 handler。它作为独立编排层负责：

1. receive screenshot set
2. register / validate images
3. preprocess images
4. call vision gateway
5. load session
6. call retrieval
7. build prompt
8. stream answer
9. store screenshot answer history
10. record usage

原因：

- 截图回答和文字问答共享 session / retrieval / usage 思想，但输入媒介不同
- 保持截图服务的独立性，更方便后续优化图像处理和视觉模型
- 避免让文字问答 API 变得过载

备选方案：

- 把截图回答塞进 Chat Service：实现快，但会让输入类型、状态机和 provider gateway 混在一起

### 2. Separate image upload registration from screenshot answer generation

截图回答不直接接收裸图片字节进入生成层，而是拆成：

- image upload / registration
- preprocessing metadata
- screenshot answer task creation

原因：

- 原型已经有“先预览、再确认提交”的用户路径
- 便于支持多图、失败重试和审计状态
- 让图片验证、压缩、格式转换与回答生成解耦

备选方案：

- 一次 HTTP 请求里同时上传图片并直接生成回答：短期方便，但扩展性和重试体验较差

### 3. Keep visual understanding behind a provider-agnostic Vision Gateway

第一版默认通过 Qwen Vision 处理图片，但 Screenshot Answer Service 只依赖抽象 Vision Gateway。Gateway 负责：

- image input normalization
- provider request / response mapping
- multi-image packaging
- vision usage extraction
- provider-specific retry / error mapping

原因：

- 你已经明确希望后续可以切换模型路线
- 视觉模型的输入格式差异通常比文本模型更大
- 可以把“Qwen Vision first”与“future replaceable”同时满足

备选方案：

- 直接在 screenshot service 里耦合 Qwen Vision API：更快，但未来替换成本高

### 4. Treat a screenshot answer as an ordered multi-image task

一次 Screenshot Answer Task 以“任务”建模，而不是以单图临时调用建模。任务包含：

- task identity
- session id
- ordered image references
- preprocessing outputs
- vision summary
- answer stream state
- final answer state

原因：

- 多张截图本身有顺序语义
- 有利于支持预览、失败、重试和历史恢复
- 与 Chat Service 的 answer-task 状态机保持一致

备选方案：

- 每张图单独生成后客户端合并：实现快，但很难保证回答一致性

### 5. Build screenshot prompts from vision summary + retrieval context + session context

Prompt Builder 不直接接收原始图像，而是接收视觉模型输出的结构化图像理解摘要，再叠加：

- Interview Session context
- Retrieval context
- prompt template
- user optional instruction

原因：

- 保持 prompt builder 不依赖 provider 原始图像协议
- 更利于日志脱敏和 Prompt 复用
- 使 Screenshot Answer Service 与 Chat Service 的 prompt strategy 接近

备选方案：

- 在 prompt builder 中混入图像协议细节：会导致后续更换视觉 provider 更麻烦

### 6. Reuse session-scoped history and usage conventions

截图回答历史、usage、日志和会话上下文应尽量与 Chat Service 对齐：

- screenshot question / task entry into session context
- screenshot answer record
- session-scoped usage attribution
- structured logs with image count and provider info

原因：

- 便于统一恢复历史和后续计费
- 让前端实时页可以用相似方式读取历史
- 减少两条生成链路在 observability 上的割裂

备选方案：

- 完全独立保存截图历史：能实现，但会让会话复盘和统一统计更复杂

### 7. Keep logs and storage image-minimized

普通日志和常规会话记录不保存完整图片二进制，也不在日志中输出完整 OCR/vision 原文。只记录：

- task id
- session id
- image count
- provider / model
- prompt version
- status
- usage
- error code

必要时把图片对象键和摘要保存在受控记录中。

原因：

- 截图内容往往比文字更敏感
- 题目截图、面试内容和个人信息都可能混在图像里
- 仍需保留足够的定位能力

备选方案：

- 在日志里记录 OCR / vision 原文：调试方便，但隐私风险太高

### 8. Keep screenshot answer streaming semantics aligned with live-answer

截图回答也采用任务状态机和有序 chunks：

- `queued`
- `processing-images`
- `vision-running`
- `streaming`
- `completed`
- `failed`
- `cancelled`（可后续扩展）

原因：

- 与现有实时回答区域的体验语义一致
- 有利于复用前端流式展示能力
- 明确把“视觉处理中”和“正在输出答案”区分开来

备选方案：

- 截图回答只做同步返回：简单，但与当前产品原型不够一致

## Risks / Trade-offs

- [Risk] 多图输入会拉长单次任务时延 → Mitigation: 对图片数量、尺寸和预处理预算做限制，并把状态机拆成 preprocessing / vision / streaming
- [Risk] Vision 输出不稳定会影响最终回答质量 → Mitigation: 通过结构化 vision summary、prompt template 和 retrieval grounding 降低漂移
- [Risk] 图片内容更敏感，日志和历史更容易泄露 → Mitigation: 普通日志不存图像正文，仅保存对象引用、摘要和最小元信息
- [Risk] Screenshot 与 Chat 两条链路过于相似，造成重复实现 → Mitigation: 共享 session / retrieval / prompt / usage 约定，但保留独立 orchestration 层
- [Risk] 多图组合顺序错误会导致回答偏差 → Mitigation: 把图像顺序作为正式输入契约，而不是隐式依赖客户端数组行为

## Migration Plan

1. 在 OpenSpec 中定义 Screenshot Answer Service 的能力、状态和边界
2. 在 `apps/backend` 中建立截图上传登记、图片预处理、Vision Gateway、Prompt Builder 和 screenshot answer task
3. 让服务消费 Interview Session 和 Knowledge Retrieval Service，而不是直连向量或会话底层存储
4. 接入流式回答、历史记录、usage 和结构化日志
5. 后续再通过独立变更接入更复杂的图片编辑、取消任务或 Speech 联动能力

回滚策略：

- 如果 Vision Provider 适配存在问题，可回退到 Screenshot Answer Service 内部的同步 mock/fallback，不影响 Chat、Session 和 Retrieval 主链路
- 如果图片预处理策略不稳定，可限制回滚在 upload / preprocess / gateway 层内部，不回退前端原型流程

## Open Questions

- 第一版 screenshot history 是否保存完整 vision summary，还是只保存 answer task 摘要和 provider 引用？
- 多张截图是否需要第一版就支持“主图 / 辅图”语义，还是只保留上传顺序？
- 图片预处理是否要在第一版就支持自动压缩和方向修正，还是先只做格式和尺寸校验？
- 是否需要把截图回答与普通回答共用一套 answer-task id 前缀和统一历史查询接口？
