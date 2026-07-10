## Why

当前项目已经建立了统一 Document Service 来管理 Resume、JD 和 Knowledge Base 的文件生命周期，但这些文档上传后仍缺少一条统一、可扩展、生产级的异步处理链路。现在需要把“上传成功”和“内容可被 AI 使用”正式解耦，建立统一 Document Processing Pipeline，保证所有文档都能经过一致的解析、标准化、分块、向量化和状态回写流程，而不改变现有产品原型交互。

## What Changes

- 新增统一的生产级 Document Processing Pipeline，作为 Resume、JD、Knowledge Base 共用的异步文档处理流水线
- 上传接口继续立即返回，后台异步创建和执行处理任务，不阻塞前端原型上传体验
- 定义处理流程：OSS → Processing Task → MinerU 解析 → Markdown 标准化 → Chunk → Embedding → pgvector 存储 → 状态更新
- 建立统一 Processing Task 数据模型、状态机、日志、配置和状态查询 API
- 支持失败自动重试、人工重新解析和未来新增文档类型扩展
- 明确本次只覆盖文档处理和向量化基础设施，不实现 Chat Service、RAG 检索编排、Prompt 拼接或 LLM 调用

## Capabilities

### New Capabilities
- `document-processing-pipeline`: 定义 Resume、JD、Knowledge Base 共享的异步文档解析、标准化、分块、向量化与状态管理流水线

### Modified Capabilities
- None

## Impact

- Affected backend: `apps/backend` 的异步任务框架、文档处理服务、状态机、内部 API 与 pgvector 写入边界
- Affected data: Processing Task 元数据、处理阶段状态、重试记录、日志关联字段和向量存储表结构
- Affected document flow: 统一 Document Service 上传完成后进入后台处理队列，而不是由各模块自行处理
- Affected future AI systems: 后续 AI 面试问答和知识检索都将基于该流水线产出的标准文本、chunk 和 embedding 数据
