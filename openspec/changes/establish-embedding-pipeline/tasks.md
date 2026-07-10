## 1. Embedding pipeline architecture

- [x] 1.1 定义统一 Embedding Pipeline 接口、输入输出模型和 Markdown 交接契约
- [x] 1.2 建立 Cleaner、Chunk Splitter、Metadata Builder、Embedding Service、Vector Store 的模块边界
- [x] 1.3 明确 Parser、Embedding Pipeline 与 Processing Pipeline 的职责划分，保证 Parser 与向量化解耦

## 2. Chunking, embedding, and vector persistence

- [x] 2.1 设计支持 Resume、JD、Knowledge Base 的 Chunk 策略注册和配置管理
- [x] 2.2 定义批量 Embedding、模型切换、错误分类和 retryable 约定
- [x] 2.3 设计 pgvector 写入模型、chunk metadata 结构和向量版本 / rebuild 标记

## 3. Status, rebuild, and verification

- [x] 3.1 定义 Embedding Task、阶段状态、失败重试和人工重新构建向量入口
- [x] 3.2 设计结构化日志、批处理观测指标和敏感信息脱敏规则
- [x] 3.3 运行 `openspec validate establish-embedding-pipeline --strict`
