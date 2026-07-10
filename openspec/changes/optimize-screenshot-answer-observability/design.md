## Context

截屏回答服务当前面向全屏线上笔试、代码题、系统设计题和报错排查题。用户使用时通常不会手动框选题目区域，因此优化不能依赖截图裁剪。现有链路已经将截图回答从 base64 大请求改为 OSS 签名 URL，并把上传接口改为非阻塞后台处理，但用户仍需要知道当前卡在上传、OSS、视觉模型还是答案保存。

当前性能观测来自一次性脚本和日志，不适合作为产品内持续诊断能力。下一步需要把阶段和耗时固化到后端任务记录、API 响应和本地自测报告里，让用户和开发者都能看清楚“工程链路已经完成，正在等模型”。

## Goals / Non-Goals

**Goals:**

- 让截屏回答在 2 秒内进入明确的“识别中/生成中”状态，即使最终答案仍受视觉模型耗时影响。
- 为每次截屏回答记录可复测的阶段耗时，包括桌面压缩、上传返回、OSS 写入、签名 URL、视觉模型、答案保存和总耗时。
- 在面试页显示用户可理解的阶段进度和失败原因，避免只有 `Failed to fetch` 或泛化等待文案。
- 生成本地性能报告，用指定图片跑完整链路并输出每个环节耗时。
- 不把原始截图、base64 图像或敏感图像内容写入诊断报告。

**Non-Goals:**

- 不更换 `qwen3.6-flash` 或改变视觉模型供应商。
- 不加入手动截图区域裁剪，因为全屏面试/笔试使用场景不适合中断用户操作。
- 不让截屏回答使用简历、JD 或知识库 RAG。
- 不在本次引入生产级队列系统；保留当前原型可替换的后台任务结构。

## Decisions

### Decision: Keep full-screen capture and automatic compression

桌面端继续截取用户选择的全屏显示器，并自动压缩到视觉模型友好的 JPEG。替代方案是手动框选区域，但会打断面试/笔试节奏，也不符合当前用户对全屏使用的预期。

### Decision: Treat model latency as observed, not optimized by switching providers

本次继续使用现有 `qwen3.6-flash`。系统只记录模型调用耗时和模型名，不通过换模型规避耗时。替代方案是引入多模型路由，但会扩大产品和成本决策范围，不适合本次变更。

### Decision: Store timing metadata alongside screenshot answer task/request

后端在 remote capture request 和 answer task 的生命周期中记录阶段指标。响应可以返回轻量指标，性能报告也从这些指标生成。替代方案是只依赖日志，但日志不易在前端展示，也不便于用户复测。

### Decision: Use stable stage names for web progress

后端阶段继续围绕 `requested`、`claimed`、`uploaded`、`vision-running`、`completed`、`failed`、`cancelled`，前端将其映射为产品文案。替代方案是前端猜测状态，但会导致“已上传”和“模型处理中”无法区分。

### Decision: Keep diagnostics metadata-only

性能报告只包含 request id、task id、尺寸、字节数、耗时、模型名、错误码和状态，不包含原始图片、base64、截图 OCR 文本或敏感内容。这样既能定位性能问题，也降低隐私风险。

## Risks / Trade-offs

- [Risk] FastAPI background task 在本地原型可用，但进程重启会丢任务。→ Mitigation: 本次记录为原型阶段实现，商业化阶段再替换为 Redis/Celery/RQ/Arq 等持久任务队列。
- [Risk] 视觉模型耗时波动仍会导致最终答案慢。→ Mitigation: 前端明确显示“正在生成答案”，telemetry 标出模型耗时，避免误判为上传失败。
- [Risk] 过度压缩可能影响小字和代码识别。→ Mitigation: 保留可配置长边和 JPEG quality，并在性能报告中记录压缩后尺寸和字节数。
- [Risk] 暴露过多诊断字段会增加隐私风险。→ Mitigation: 明确禁止诊断报告保存原始截图、base64 图像和截图正文内容。

## Migration Plan

1. 扩展后端截屏任务/请求响应中的阶段耗时元数据，保持现有字段向后兼容。
2. 更新桌面端上传元数据，上报压缩后尺寸和字节数。
3. 更新 Web 截屏回答 UI，将阶段映射为清晰进度和错误提示。
4. 增加本地性能自测脚本，输出 `artifacts/perf/` 报告。
5. 运行后端回归测试、桌面 typecheck、Web typecheck，并用指定图片做端到端性能自测。

## Open Questions

- 是否需要把性能报告入口暴露到后台管理页，还是仅保留本地开发报告。
- 截屏临时 OSS 对象的生产生命周期策略是否需要在本次同步落地，还是沿用现有对象清理策略。
