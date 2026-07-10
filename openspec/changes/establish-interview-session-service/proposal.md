## Why

当前产品原型已经有“创建面试、继续面试、选择本场资料、进入实时工作台、结束后恢复历史”的明确流程，但服务端还没有统一的 Interview Session Service 去承载这些状态。随着后续 Chat Service、Retrieval Service、桌面收音桥接和计费都要围绕“同一场面试”协作，现在需要先建立统一会话模型，避免资料绑定、上下文、配置和用量分散在多个模块里。

## What Changes

- 新增统一 Interview Session Service，负责创建、读取、恢复、结束和重新开始一次 AI 面试会话。
- 为会话建立权威生命周期状态，覆盖准备中、进行中、已结束和可恢复历史等场景。
- 支持在一次会话中绑定多份 Resume、JD 和 Knowledge Base 文档，并保存会话级资料快照与确认版本。
- 支持保存会话级模型配置、Prompt 配置和 Retrieval 配置，为后续 Chat Service 提供统一输入上下文。
- 支持管理多轮 Conversation Context，包括用户、面试官、系统与 AI 建议相关的结构化会话记录边界。
- 支持会话级 Token 使用统计、查询和汇总，为后续计费、限额和分析提供基础。
- 保持当前产品原型交互不变：继续面试、恢复历史、结束面试和重新开始面试仍沿用既有页面与动作语义。

## Capabilities

### New Capabilities
- `interview-session-service`: 定义统一面试会话的生命周期、资料绑定、配置快照、上下文管理、用量统计和历史恢复能力

### Modified Capabilities
- None.

## Impact

- Affected code: `apps/backend/app/modules/session.py`、会话相关 schemas / services / repository / deps、后续与 retrieval / answer / screenshot / desktop bridge 的会话接入边界
- APIs: 新增会话创建、详情查询、列表恢复、结束、重新开始、上下文追加与用量查询接口
- Data model: 新增 Interview Session、Session Material Binding、Session Config Snapshot、Conversation Context、Session Usage 等核心实体
- Systems: 为 Chat Service、Knowledge Retrieval Service、桌面音频桥接和计费系统提供统一的会话主键与上下文来源
