## Why

OfferSteady 当前已能跑通资料上传、OSS 存储、MinerU 解析、RAG 和面试回答，但这些能力仍偏原型化：长任务和 API 请求边界不清、OSS artifact 缺少显式清单、处理/删除任务缺少持久重试、模型用量和 RAG 命中缺少审计。为了支撑商业化使用，需要在不改变原型核心页面的基础上补齐数据一致性、可恢复性、计费审计和模型职责边界。

## What Changes

- 引入商业化分层：API 层只做鉴权、轻量校验、状态查询和任务创建；Worker/Queue 负责资料处理、删除清理、同步校验和失败重试。
- 增加 material artifact manifest：每个 document version 显式记录 original、normalized Markdown、chunks、deletion marker 等 OSS artifacts 及同步状态。
- 增加 durable job 体系：processing jobs、deletion jobs、reconcile jobs 记录 stage、status、retry count、safe error code 和 timestamps。
- 增加模型用量与成本审计：MinerU、qwen3-vl、Embedding、Rerank、Chat 均通过后端 adapter 调用并记录安全 usage。
- 增加 RAG retrieval trace：记录检索过滤范围、候选数量、重排数量、返回数量和来源版本，不记录敏感全文。
- 固化模型职责边界：qwen3-vl 只用于截图/拍照识别，Chat 模型只用于最终回答，Embedding/Rerank 只用于知识库检索链路。
- 增加商业化安全边界：DB、OSS key、session material binding、RAG filters 全链路按 owner_user_id 隔离。
- 保持当前产品原型布局不变，不引入管理后台、多租户团队空间或复杂运营系统。

## Capabilities

### New Capabilities
- `commercial-job-orchestration`: API 与 Worker/Queue 的职责分离，以及资料处理、删除、同步校验任务的持久状态、重试和错误记录。
- `material-artifact-manifest`: 资料版本对应 OSS artifacts 的显式清单、同步状态、校验时间和前端可解释状态。
- `ai-usage-and-rag-observability`: 模型用量审计、RAG trace、模型适配器边界和隐私安全日志。
- `commercial-security-isolation`: 用户级数据隔离、OSS key 约束、session material binding 权限校验和 RAG filter 安全边界。

### Modified Capabilities
- None.

## Impact

- `apps/backend`: Document Service、Document Processing、Material Availability、Session Service、Chat/Screenshot Answer Service、Provider Adapters、Postgres persistence、logging/usage boundaries。
- `apps/web`: 资料库同步状态、任务状态、不可用原因和回答来源展示，不改变页面主结构。
- `packages/protocol`: artifact manifest、job status、usage record、RAG trace、safe sync status 类型。
- `infra`: 后续承载 Worker/Queue、后台任务运行方式和数据库迁移。
- `docs`: 更新商业化架构、数据一致性、模型职责边界和运维诊断说明。
- 隐私影响：usage、trace 和日志只保存安全摘要、ID、计数和错误码，不保存简历全文、JD 全文、截图原图、完整 Prompt、embedding 或供应商 payload。
