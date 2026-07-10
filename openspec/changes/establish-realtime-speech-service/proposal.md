## Why

当前 OfferSteady 已经有 Interview Session、Knowledge Retrieval、Chat Service 和 Screenshot Answer Service，但“实时语音辅助”仍停留在原型和拆散的能力定义中，还没有一个正式的 Realtime Speech Service 去承接音频流、字幕、问题识别与自动回答。现在需要建立统一实时语音服务，让电脑端收音、Web 端实时字幕和 AI 回答形成一条正式后端链路，并与现有产品原型保持一致。

## What Changes

- 新增统一 Realtime Speech Service，负责实时音频接入、转写、问题识别、Chat 调用、流式回答和会话内记录。
- 建立面向已授权采集端的 WebSocket 实时连接边界，支持会话绑定、低延迟音频上传、状态同步和重连恢复。
- 建立可替换的 Realtime ASR Gateway，第一版以 Qwen Realtime ASR 为默认目标，但保持后续可切换不同实时语音模型。
- 建立实时字幕、转写修订、问题候选与问题确认事件模型，并与现有“我 / 面试官”双角色原型保持一致。
- 建立从转写到问题识别再到 Chat Service 的统一编排层，使 Resume、JD、Knowledge 的检索增强继续通过既有 Session + Retrieval + Chat 边界生效。
- 建立 Conversation Storage、Usage、结构化日志和降级策略，但不扩展到登录、支付或后台管理。

## Capabilities

### New Capabilities
- `realtime-speech-service`: 定义实时音频接入、WebSocket 会话绑定、ASR、字幕、问题识别、Chat 编排和会话级记录能力

### Modified Capabilities
- None.

## Impact

- Affected code: `apps/backend` 的实时语音模块、WebSocket 会话层、ASR gateway、问题识别编排、会话上下文写入和 Chat 调用边界
- APIs: 新增实时语音 WebSocket / 控制 API、字幕事件流、问题检测状态、实时回答触发和历史查询接口
- Dependencies: Interview Session Service、Knowledge Retrieval Service、Chat Service、desktop / web audio publisher、ASR provider adapter、session usage and logging
- AI assets: 新增实时语音 Prompt / eval 边界、问题识别策略和 `ai/evals/` 样例
- Product behavior: 保持当前产品原型交互不变，让实时对话区和回答区获得正式服务端支持
