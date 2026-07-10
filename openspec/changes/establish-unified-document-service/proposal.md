## Why

当前产品原型已经把 Resume、JD、Knowledge Base 作为面试准备的核心输入，但服务端仍缺少真正统一的文档生命周期能力。现在需要先把“文件怎么上传、存哪里、如何命名、谁能看、如何删除、何时可交给后续处理”这层单独建立起来，避免后面解析、RAG 和面试链路各自重复实现一套文档管理逻辑。

## What Changes

- 新增统一 Document Service，作为 Resume、JD、Knowledge Base 共用的文件生命周期管理能力
- 覆盖上传、格式校验、大小校验、唯一命名、OSS 存储、PostgreSQL 元数据登记、状态流转、删除、列表和权限控制
- 将 Resume、JD、Knowledge 文件上传从“按模块各自处理”收敛为“按文档类型复用统一服务”
- 为后续 Document Processing Pipeline 预留稳定的处理入口与交接状态，但本次不实现解析、Markdown 转换、Chunk、Embedding、向量检索或 RAG
- 统一定义文档状态模型，使前端和后端都能明确区分上传中、已上传、处理中、可用、删除中、已删除、失败等状态

## Capabilities

### New Capabilities
- `document-service-lifecycle`: 统一定义 Resume、JD、Knowledge 文档的上传、存储、元数据、状态、列表、删除和权限行为

### Modified Capabilities
- None

## Impact

- Affected backend: `apps/backend` 的文档 API、Document Service、OSS 适配器、数据库元数据层、权限校验与状态管理
- Affected frontend: `apps/web` 资料页上传、文件列表、删除和状态展示的后端联调方式
- Affected storage: 阿里云 OSS 对象键规范、软删除/物理删除策略、后续处理入口
- Affected data: PostgreSQL 中统一文档元数据模型、文档归属、文档类型、状态和处理交接字段
- Affected future systems: 后续 Document Processing Pipeline 只消费文档服务暴露的受控入口和状态，不直接接管上传链路
