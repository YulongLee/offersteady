## 1. Retrieval service architecture

- [x] 1.1 定义统一 Knowledge Retrieval Service 接口、输入输出模型和 Chat 解耦契约
- [x] 1.2 建立 Query Embedding、Vector Search、Metadata Filter、Reranker、Context Builder 的模块边界
- [x] 1.3 明确 Retrieval Service 与 Embedding Pipeline、Chat Service 的职责划分

## 2. Retrieval pipeline and ranking

- [x] 2.1 设计支持 Resume、JD、Knowledge Base 联合检索的 metadata filter 与召回策略
- [x] 2.2 定义 TopK 配置、query embedding provider 和不同检索策略的运行时配置方案
- [x] 2.3 设计 reranker 和 context builder 的输入输出、排序规则与结构化上下文结果

## 3. API, observability, and verification

- [x] 3.1 设计 Retrieval API、结果结构、过滤条件和错误返回约定
- [x] 3.2 定义 Retrieval 日志、敏感信息脱敏和效果观测字段
- [x] 3.3 运行 `openspec validate establish-knowledge-retrieval-service --strict`
