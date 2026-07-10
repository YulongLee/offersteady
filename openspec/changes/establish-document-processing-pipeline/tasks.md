## 1. Pipeline architecture and task model

- [x] 1.1 定义统一 Processing Task 数据模型、阶段状态、重试字段和日志关联字段
- [x] 1.2 设计 Document Service 与 Processing Pipeline 的交接契约，确保上传完成后立即返回并异步创建任务
- [x] 1.3 设计共享 Pipeline 的文档类型注册机制，支持 Resume、JD、Knowledge Base 和未来扩展类型

## 2. Asynchronous execution framework

- [x] 2.1 设计后台异步执行框架，包括任务领取、阶段推进、失败处理和恢复策略
- [x] 2.2 定义 MinerU 解析、Markdown 标准化、Chunk Splitter、Embedding Service、pgvector 存储的适配器边界
- [x] 2.3 设计自动重试和人工重新解析机制，明确可恢复失败与永久失败规则

## 3. API, observability, and configuration

- [x] 3.1 设计 Processing API，包括任务创建触发方式、状态查询和人工重新解析入口
- [x] 3.2 定义 Pipeline 配置和结构化日志约定，确保不记录敏感正文、chunk 内容或 embedding 向量
- [x] 3.3 校验方案与现有产品原型和系统架构一致，运行 `openspec validate establish-document-processing-pipeline --strict`
