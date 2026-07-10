## Context

OfferSteady 当前原型已经打通用户资料上传、OSS 存储、MinerU 解析、Markdown/chunks 处理、Embedding/Rerank、面试资料绑定和回答生成。但这些能力目前仍以 MVP 直连方式为主，部分长耗时处理可能发生在 API 进程内，OSS artifacts 主要通过路径约定推导，模型调用和 RAG 检索缺少商业化用量、成本和排障记录。

本设计在不改变当前核心页面和用户流程的前提下，补齐商业化底座：API/Worker 分层、artifact manifest、durable jobs、AI usage、RAG trace、安全隔离和隐私日志边界。

## Goals / Non-Goals

**Goals:**

- 让长耗时资料处理、删除清理和同步校验从 API 请求路径中解耦。
- 让每个 ready/selectable 资料版本都能由数据库 artifact manifest 解释其 OSS 产物状态。
- 让处理、删除和同步任务可重试、可恢复、可观察。
- 让 MinerU、qwen3-vl、Embedding、Rerank、Chat 的调用可计费、可审计、可替换。
- 让 RAG 检索过程可排障，但不记录敏感全文。
- 强化 owner_user_id 级隔离，避免跨用户资料、OSS object、RAG chunk 或 session 绑定泄漏。

**Non-Goals:**

- 不新增运营管理后台。
- 不引入团队多租户、企业组织或权限角色体系。
- 不改变当前 Web 原型主页面布局。
- 不实现复杂工作流引擎；原型阶段可以用数据库 job 表和本地 worker loop 起步。
- 不保存完整 Prompt、截图原图、embedding 向量明文日志或供应商原始 payload。

## Decisions

### 1. Split API and Worker responsibilities

API 层负责鉴权、轻量校验、创建任务、保存业务快照和查询状态。Worker 层负责 MinerU 解析、Markdown 归一化、chunking、embedding、vector indexing、OSS/DB reconciliation 和 deletion cleanup。

替代方案是继续在 API 请求中同步处理。它实现简单，但无法承受大文件、供应商超时、并发上传和删除失败重试，不适合商业化。

### 2. Use durable database jobs before introducing external queue infrastructure

首版可以用 PostgreSQL job 表作为 durable queue，由 Worker 定期拉取 queued/retrying 任务执行。后续并发规模上来后，再替换或补充 Redis、RabbitMQ、Celery、Temporal 等队列/工作流组件。

替代方案是立即引入完整外部队列。它更标准，但会提前增加部署复杂度；当前产品仍处于 MVP 到商业化底座过渡阶段，数据库队列更可控。

### 3. Persist artifact manifest as first-class state

每个 material document version 显式保存 original、normalized_markdown、chunk_manifest、deletion_marker 等 artifact 记录，包括 object_key、content_type、size_bytes、sha256、sync_status 和 verified_at_ms。

替代方案是通过固定路径即时推导。它原型快，但用户反馈“OSS 和前端不一致”时难以解释、审计和修复。

### 4. Keep model providers behind separate adapters

MinerU、qwen3-vl、Embedding、Rerank 和 Chat 分别通过独立 Port/Adapter 接入。qwen3-vl 只负责截图/拍照识别，Chat 模型只负责最终回答，Embedding/Rerank 只负责知识库检索链路。

替代方案是用单一多模态模型完成识别和回答。它接入简单，但成本、Prompt、故障定位和评测边界会混乱。

### 5. Record safe usage and trace data

每次模型调用记录 operation_kind、provider、model、token/unit counts、points、trace_id 和关联任务 ID。RAG trace 记录 filter document versions、candidate_count、reranked_count、returned_count 和 source IDs，不记录 chunk 全文。

替代方案是不记录 usage/trace。它开发快，但商业化后无法解释成本、扣费、失败和“为什么没有使用资料”。

### 6. Enforce owner-scoped boundaries at every data access layer

所有资料记录、artifact、job、session binding、RAG retrieval filter、answer task 和 usage record 都必须绑定 owner_user_id。后端生成 OSS object key，前端不得传入任意可读取 object key。

替代方案是只在 API 入口鉴权。该方案不足以防止内部服务或后续功能绕过用户边界。

## Risks / Trade-offs

- [Risk] 数据库 job queue 在高并发下吞吐不足 -> Mitigation: 首版限制并发和重试，后续替换为外部队列时保持 JobPort 接口稳定。
- [Risk] artifact manifest 与 OSS 实际状态仍可能短暂不一致 -> Mitigation: processing 完成强校验、reconcile job 定期修复、回答前 fail-closed。
- [Risk] usage/trace 误存敏感信息 -> Mitigation: schema 层只允许 ID、计数、hash 和安全错误码，评审禁止全文字段。
- [Risk] Worker 失败导致资料长期 processing -> Mitigation: job retry_count、safe_error_code、前端可见状态和手动重试入口。
- [Risk] 增加表和状态导致实现复杂 -> Mitigation: 分阶段落地，先 artifact/jobs/usage 最小字段，再扩展运营能力。

## Migration Plan

1. 增加协议类型和数据库表：material_artifacts、material_processing_jobs、material_deletion_jobs、ai_usage_records、rag_retrieval_traces。
2. 抽象 JobPort/Worker loop，先支持本地进程或独立命令运行。
3. 将资料处理完成后的 artifact verification 写入 material_artifacts。
4. 将删除逻辑改为 DB tombstone + deletion job + cleanup retry。
5. 将模型调用统一记录 safe usage。
6. 将 RAG retrieval 记录 safe trace。
7. 增加 owner_user_id 隔离测试和商业化 readiness 检查。
8. 回滚时保留新增表，不删除用户资料；API 可回退到旧处理路径但继续保持前端不可见敏感数据。

## Open Questions

- 首版 Worker 是作为独立 CLI 进程运行，还是随 uvicorn 启动一个受控 background loop？
- RAG trace 中是否需要保存短 evidence 摘要，还是只保存 source IDs 和计数？
- 计费记录是否在本变更内真正扣点，还是只先记录 usage/cost trace？
