## Context

当前系统已经具备统一 Document Service 和 Document Processing Pipeline 骨架，上传后的文档能够进入异步任务状态机，但真正的解析能力仍停留在通用占位适配器层。随着后续 Chunk、Embedding、pgvector 和 RAG 都要建立在“统一文本输入”之上，解析层需要尽快从 Pipeline 中拆出来，形成一个可独立替换、可独立观测、可独立测试的 Document Parser Service。

当前解析相关约束很明确：

- 不改变前端原型、上传流程和资料使用交互
- Resume、JD、Knowledge Base 都要进入同一套解析能力
- Parser 必须输出统一 Markdown，不能让下游按文件格式分别处理
- Parser 不负责 Chunk、Embedding、向量写入或问答链路
- 日志和错误处理必须避免泄露简历、JD、知识库正文

## Goals / Non-Goals

**Goals:**

- 建立独立的 Document Parser Service，作为 Processing Pipeline 的下游解析边界
- 集成 MinerU 作为主解析提供方，并覆盖 PDF、DOCX、DOC、TXT、Markdown 输入
- 定义统一的 Parser 输入、输出、状态回传和错误分类契约
- 把非结构化文档统一转换成标准 Markdown，供 Chunk 和 Embedding 复用
- 为 Parser 增加结构化日志、失败分类和可恢复错误约定
- 保持外部解析器和文件加载能力可替换，不把实现硬编码进 Pipeline

**Non-Goals:**

- 不实现 Chunk Splitter
- 不实现 Embedding Service
- 不实现 pgvector 写入
- 不实现 RAG 检索、Prompt 拼接或 Chat Service
- 不修改前端原型页面、文案或交互顺序

## Decisions

### 1. 采用“Pipeline 调度 + Parser 执行”的双层边界

Processing Pipeline 只负责任务领取、阶段推进、重试编排和整体状态机；Document Parser Service 只负责接收文档定位信息、选择解析器、输出标准 Markdown，并回传解析结果与解析阶段状态。

原因：

- 保持 Pipeline 轻量，只承担调度职责
- 让 Parser 能独立测试、独立替换、独立观测
- 避免把格式识别、文档预处理、文本标准化逻辑继续塞进任务调度器

备选方案：

- 继续把解析逻辑放在 Pipeline service 内：实现更快，但后续接 MinerU、格式扩展、错误治理时会迅速膨胀

### 2. 采用统一 Parser 接口，按文件格式路由到具体适配器

Parser Service 对外暴露一个统一接口，例如：

- 输入：document_id、object_key、document_kind、file_kind、content_type、task_id
- 输出：normalized_markdown、parser_provider、detected_title、metadata、warnings

内部按文件格式路由：

- PDF / DOCX / DOC → MinerU 解析适配器
- TXT / Markdown → 轻量文本加载适配器 + Markdown 标准化

原因：

- 对下游隐藏格式差异
- 后续新增文件类型时只需要新增 format adapter
- 允许同一服务内同时存在“复杂格式解析”和“纯文本标准化”两类路径

备选方案：

- 所有文件都强制走 MinerU：路径统一，但对 TXT / Markdown 属于不必要的重处理

### 3. Markdown 标准化作为 Parser Service 内部固定阶段

无论原始输入来自 MinerU 还是纯文本文件，Parser Service 都必须在返回前完成 Markdown 标准化，输出统一结构。

标准化范围包括：

- 统一换行与空白规范
- 移除解析噪声和空段落
- 规范标题层级与列表格式
- 附加最小文档头信息（如文档类型或来源提示）时保持可配置

原因：

- 下游 Chunk 和 Embedding 只依赖一种文本形态
- 减少每个下游阶段重复清洗文本
- 让解析质量问题收敛在 Parser 层治理

备选方案：

- 把标准化延后到 Chunk 阶段：会让文本清洗职责分散，增加调试成本

### 4. Parser Service 通过独立状态回写端口更新解析阶段状态

Parser 需要更新 Processing Status，但不能直接接管整条 Pipeline 状态机。因此设计一个独立的状态记录边界，例如 `ParserStatusPort` / `ProcessingTaskReporter`：

- `mark_parsing_started`
- `mark_parsing_succeeded`
- `mark_parsing_failed`

Pipeline 在调用 Parser 前后仍维护任务上下文与后续阶段调度；Parser 只负责“解析阶段”的状态和错误回传。

原因：

- 满足“Parser 更新 Processing Status”的需求
- 同时保持 Pipeline 与 Parser 解耦
- 避免 Parser 直接理解 Chunk / Embedding / Completion 等后续状态

备选方案：

- Parser 完全不写状态，只返回结果：边界最干净，但不满足你希望 Parser 自己能回写解析状态的要求
- Parser 直接操作整个任务状态机：耦合过深，会侵入 Pipeline 职责

### 5. 错误分类分为可恢复解析失败和永久格式失败

Parser 错误分两类：

- 可恢复错误：MinerU 临时不可用、OSS 下载失败、网络波动、超时
- 永久错误：文件格式伪装、文档损坏、空文件、编码不可识别、超出解析支持边界

返回结构至少包含：

- `error_code`
- `error_type`
- `retryable`
- `provider_name`
- `message_safe_for_log`

原因：

- 让 Pipeline 能基于 `retryable` 做自动重试
- 让状态查询 API 能展示一致的失败摘要
- 避免把底层原始异常直接暴露给调用方

备选方案：

- 统一把所有失败都视为可重试：实现简单，但会浪费资源并掩盖永久失败

### 6. 结构化日志只记录元数据，不记录原始正文

Parser 日志记录以下字段：

- task_id
- document_id
- document_kind
- file_kind
- parser_provider
- action
- duration_ms
- retry_count
- error_code

禁止记录：

- 简历 / JD / 知识库正文
- 解析后的 Markdown 全文
- 文档截图内容
- embedding 或 chunk 文本

原因：

- 满足敏感资料最小暴露原则
- 让生产排障仍有足够上下文

备选方案：

- 将 Markdown 片段写入日志辅助排查：短期方便，但长期存在数据泄露风险

### 7. MinerU 集成保持运行方式可替换

设计上只绑定 `MineruParserAdapter` 这个抽象，不提前锁死具体运行形态。实现阶段可选择：

- 本地 Python 库调用
- 独立内部容器服务
- 独立解析微服务

原因：

- 当前仓库仍处于 MVP 演进阶段，真实部署形态可能随稳定性和资源成本调整
- 先固化契约，再决定运行时封装方式更稳妥

备选方案：

- 在设计阶段就绑定“必须是独立服务”：架构清晰，但会过早增加部署复杂度

## Risks / Trade-offs

- [Risk] MinerU 对复杂版式 PDF / DOC 解析结果不稳定 → Mitigation: 统一进入 Markdown 标准化并记录 parser warnings，允许失败重试与人工复解析
- [Risk] TXT / Markdown 与 PDF / DOCX 走不同解析路径后输出风格不一致 → Mitigation: 强制所有结果都经过同一标准化阶段
- [Risk] Parser 状态回写与 Pipeline 状态推进出现重复或冲突 → Mitigation: 只允许 Parser 写入 parsing 阶段相关状态，其他阶段仍归 Pipeline 管理
- [Risk] 未来引入多种解析供应商后适配器激增 → Mitigation: 固化统一输入输出接口和错误分类，不让上层感知供应商差异
- [Risk] 原始文档内容进入日志或异常消息 → Mitigation: 统一安全错误对象和结构化日志字段，禁止直接记录原始解析结果

## Migration Plan

1. 在 OpenSpec 中先定义 Document Parser Service 的能力边界、输入输出和状态协作规则
2. 实现阶段新增 Parser Service、格式路由器、MinerU 适配器和文本标准化器
3. 将现有 Processing Pipeline 的解析占位适配器替换为对 Parser Service 的调用
4. 接入解析阶段状态回写、错误分类和结构化日志
5. 由后续变更继续接入真实 Chunk / Embedding / pgvector 链路

## Open Questions

- MinerU 第一版以 Python 包内嵌运行，还是独立服务运行更合适？
- DOC 解析是否直接交给 MinerU，还是先转中间格式再解析更稳？
- Markdown 标准化是否需要从第一版开始注入“文档类型头部信息”，还是先保持最轻输出？
- 解析 warnings 是否需要暴露到对外状态查询 API，还是只保留内部日志与任务事件？
