## 1. Parser service architecture

- [x] 1.1 定义统一 Document Parser Service 接口、输入输出模型和解析阶段状态回写契约
- [x] 1.2 建立按文件格式路由的解析器注册机制，覆盖 PDF、DOCX、DOC、TXT、Markdown
- [x] 1.3 明确 Parser Service 与 Processing Pipeline 的调用边界，保证 Pipeline 仅负责任务调度

## 2. Parser adapters and normalization

- [x] 2.1 集成 MinerU 解析适配器，用于 PDF、DOCX、DOC 等二进制文档解析
- [x] 2.2 实现 TXT 与 Markdown 的轻量文本加载和统一 Markdown 标准化流程
- [x] 2.3 定义解析结果结构、warnings、错误分类和 retryable 标记

## 3. Observability and verification

- [x] 3.1 增加 Parser 日志、解析耗时、错误码和敏感信息脱敏约定
- [x] 3.2 设计解析成功、解析失败、状态回写和格式兼容性的验证方案
- [x] 3.3 运行 `openspec validate establish-document-parser-service --strict`
