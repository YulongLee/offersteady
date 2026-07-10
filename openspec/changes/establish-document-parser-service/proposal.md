## Why

当前系统已经建立统一 Document Service 和异步 Document Processing Pipeline，但“文档解析”这一步仍只是流水线里的占位适配器，缺少独立、可扩展、可观测的正式服务边界。现在需要把 Parser 从 Pipeline 中单独抽离出来，统一负责 Resume、JD 和 Knowledge Base 的文档解析与 Markdown 标准化输出，避免后续 Chunk、Embedding 和处理调度继续耦合在一起。

## What Changes

- 新增独立的 Document Parser Service，统一负责所有上传文档的解析、标准化和 Markdown 输出。
- 集成 MinerU 作为主解析能力，并覆盖 PDF、DOCX、DOC、TXT、Markdown 等当前支持格式。
- 明确 Parser 与 Processing Pipeline 解耦：Pipeline 仅负责任务调度、阶段推进和状态管理，Parser 仅负责文档内容解析。
- 定义统一 Parser 输入输出契约、结构化日志、错误分类和失败回传机制。
- 让 Parser 在完成解析后输出标准 Markdown，作为后续 Chunk 和 Embedding 的统一输入。
- 保持现有前端原型和上传交互不变，不在本变更中实现 RAG 检索、Prompt 拼接或问答链路。

## Capabilities

### New Capabilities
- `document-parser-service`: 定义统一文档解析服务的输入、格式支持、Markdown 输出、错误处理与状态回写行为

### Modified Capabilities
- None

## Impact

- Affected backend: `apps/backend` 的文档处理服务、解析适配器、Processing Task 阶段协作和内部服务边界
- Affected dependencies: MinerU 集成方式、文档格式解析依赖、Markdown 标准化组件
- Affected processing flow: 解析职责将从泛化 Pipeline 适配器中抽离，形成明确的 Parser Service 边界
- Affected observability: 需要新增解析阶段日志、错误分类、格式支持检查和解析耗时指标
- No product prototype change: 不改变现有 Web 原型页面结构、资料上传入口和面试使用交互
