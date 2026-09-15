## Why

国服 Backend 容器在面试结束后仍长期维持较高内存使用率。现有运行指标显示部分 ASR 会话回收失败，且临时截图与会话级缓存存在生命周期不完整的风险，可能造成持续增长并放大容器内存压力。

## What Changes

- 面试结束、空闲超时和管理员终止统一清理所有会话级实时资源。
- 清理实时语音服务中按会话保存的缓存、计数器、状态和终止标记，避免跨会话累积。
- 为内存中的截图上传意图、待确认 payload 和已上传图片增加过期回收机制。
- 加强 ASR 连接关闭的可观测性与幂等回收，确保结束后不残留 provider session。
- 增加针对会话结束和临时上传过期的回归测试。

## Capabilities

### New Capabilities

- `interview-resource-lifecycle`: 面试会话结束后的实时资源释放与临时数据过期回收。

### Modified Capabilities

<!-- No existing spec-level requirements are changed; this is a new lifecycle capability. -->

## Impact

- `apps/backend/app/services/realtime_speech_service.py`
- `apps/backend/app/services/dashscope_realtime_asr_gateway.py`
- `apps/backend/app/services/dashscope_task_asr_gateway.py`
- `apps/backend/app/services/screenshot_answer_service.py`
- Backend realtime/session tests and runtime metrics.
- 不改变前端视觉布局、面试回答内容或外部供应商协议；截图和音频临时数据仍按最小化保存原则处理。
