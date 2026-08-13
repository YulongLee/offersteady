## Context

最终实时转录在会话进行中会以 `interviewer` 或 `candidate` 角色写入 `interview_session_context_entries`，该表随 PostgreSQL 会话持久化。当前复盘页只加载 live-answer 与 screenshot-answer 历史，没有加载这些对话项。实时 Redis 转录在结束时会被清理并受短 TTL 约束，因此不是可靠的历史来源。

## Goals / Non-Goals

**Goals:**

- 结束后仍可按原始时间顺序查看面试官和候选人的最终转录。
- 明确区分“实际对话转录”和“AI 回答建议”。
- 允许所属用户把完整复盘下载为可读、可迁移的 UTF-8 Markdown。
- 沿用会话删除边界，并保持原始音频不持久化。

**Non-Goals:**

- 保存或导出原始音频、实时未确认片段、模型 Prompt 或供应商响应。
- 自动评分候选人、生成能力结论或修改 AI 回答。
- PDF/Word 导出、服务端文件归档或公开分享链接。

## Decisions

### Use durable session context as the transcript source

复盘 API 从 `interview_session_context_entries` 读取 `realtime-system` 与 `realtime-microphone` 的最终项，并映射为面试官与我。它在读取前通过 `SessionService.get_session` 验证所属账号。

选择该方案是因为上下文已经持久、带所属用户和顺序，并会随会话删除。替代方案是读取 Redis 转录，但结束清理和 TTL 会导致历史丢失；另建转录表会重复存储同一敏感文本。

### Return one review snapshot endpoint

新增 `/api/v1/sessions/{id}/review`，一次返回场次元数据和双角色转录。问题与 AI 建议继续复用现有 answer history API，由 Web adapter 合并，避免复制已有回答数据。

### Generate Markdown entirely in the browser

Web 使用纯函数将当前复盘快照转换为 Markdown，并通过 Blob/Object URL 触发下载。这样不会新增服务器文件、OSS 数据或下载令牌。文件名经过安全清洗，内容加 UTF-8 BOM 以兼容常见中文编辑器。

### Separate transcript and AI advice visually and semantically

页面新增“真实对话记录”区域，按时间顺序显示“面试官/我”；原有“问题与回答记录”明确标注为“AI 回答建议”。导出文件也使用不同章节，避免把建议误认为候选人真实说法。

## Risks / Trade-offs

- [Risk] 旧场次没有持久上下文时转录为空 → 显示清晰空态，仍允许查看已有问题和回答建议。
- [Risk] ASR 文本可能存在识别误差 → 页面和下载中标注为“语音转写”，不称为逐字录音。
- [Risk] 很长场次生成较大 Markdown → 客户端生成是线性的；MVP 不引入服务端异步导出。
- [Risk] 敏感内容被下载到共享电脑 → 只在用户主动点击后下载，并在按钮旁提示文件包含面试对话。

## Migration Plan

1. 先发布只读 review API 和 Web adapter。
2. 发布复盘展示与本地下载，不变更数据库表。
3. 回滚时移除新 UI/API；现有上下文数据和会话行为不受影响。

## Open Questions

- 后续是否增加 PDF/Word 导出，由真实用户需求决定，不纳入本次范围。
