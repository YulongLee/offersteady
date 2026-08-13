## Why

当前面试复盘主要展示已确认问题和 AI 回答建议，没有呈现候选人实际说出的回答；结束面试后用户无法完整回顾问答过程，也不能把个人面试记录下载到本地留存。

## What Changes

- 在面试复盘中按时间顺序展示最终的“面试官”和“我”双角色转录，并明确区分真实转录与 AI 回答建议。
- 结束面试后从当前用户的持久会话上下文读取复盘记录，不依赖会被清理或过期的实时 Redis 状态。
- 新增当前场次复盘 API，返回场次信息、最终双角色转录以及现有问题/回答记录所需数据。
- 在复盘页新增“下载复盘”按钮，由浏览器生成 UTF-8 Markdown 文件，包含场次信息、对话转录和问题/AI 回答建议。
- 下载文件不上传 OSS，也不创建新的服务端附件；只有场次所属账号可以读取或导出。
- 默认不保存原始音频；转录随整场面试删除，不把未完成 ASR 片段写入复盘。

## Capabilities

### New Capabilities

- `interview-review-transcript-export`: 定义复盘双角色记录、数据来源、账号隔离和本地 Markdown 导出行为。

### Modified Capabilities

- None.

## Impact

- Backend: session review schema/API, session service and ownership tests.
- Web: review domain model, backend adapter, review page, Markdown exporter, responsive styles and tests.
- Privacy: persistent text includes personal interview speech; no raw audio is retained, exports are user-triggered and generated locally, and deletion remains session-scoped.
- No desktop companion rebuild and no change to payment, points, ASR capture, model provider, or live-answer protocol.
