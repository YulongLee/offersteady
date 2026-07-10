## ADDED Requirements

### Requirement: The system MUST provide one unified document service for Resume, JD, and Knowledge files
系统 MUST 通过统一 Document Service 管理 Resume、JD 和 Knowledge 三类文档的生命周期，而不是让每个业务模块分别维护不兼容的上传与管理行为。该服务 MUST 至少支持文档类型标识、归属用户、统一主键、对象存储位置、状态字段和受控管理接口。

#### Scenario: Resume and JD reuse the same lifecycle contract
- **WHEN** 用户分别上传 Resume 和 JD 文件
- **THEN** 系统对两者使用统一的文档主键、统一的状态模型和统一的权限边界

#### Scenario: Knowledge file enters the same service with type-specific metadata
- **WHEN** 用户上传 Knowledge 文件
- **THEN** 系统仍通过统一 Document Service 登记该文件，并仅通过文档类型或附加关联字段区分其业务归属

### Requirement: The system MUST validate file format and file size before accepting an upload intent
系统 MUST 在签发上传意图前校验文档类型、文件扩展名、MIME 类型和文件大小。前端可以提供提示，但后端 MUST 作为最终权威边界拒绝不支持的格式或超限文件。

#### Scenario: Supported format passes validation
- **WHEN** 用户上传受支持的 `pdf`、`docx`、`doc`、`txt` 或 `md` 文件且大小在允许范围内
- **THEN** 系统签发可用的上传意图

#### Scenario: Unsupported format is rejected
- **WHEN** 用户尝试上传不受支持的格式
- **THEN** 系统拒绝签发上传意图，并返回统一错误结构说明格式不被接受

#### Scenario: Oversized file is rejected
- **WHEN** 用户上传超过当前文档大小上限的文件
- **THEN** 系统拒绝签发上传意图，并返回统一错误结构说明文件超限

### Requirement: The system MUST use unique object naming and OSS-backed file storage
系统 MUST 为每个文档生成唯一对象键，并将二进制文件存放到阿里云 OSS。对象键 MUST 避免文件名冲突，并 SHALL 支持按用户、文档类型和环境进行逻辑隔离。产品层 MUST NOT 依赖原始文件名作为对象存储主键。

#### Scenario: Two users upload files with the same filename
- **WHEN** 两个不同用户分别上传同名文件
- **THEN** 系统为两个文档生成不同的对象键，且二者不会互相覆盖

#### Scenario: Same user uploads a newer file with the same display name
- **WHEN** 同一用户再次上传与旧文件同名的文档
- **THEN** 系统为新文档生成新的唯一对象键，而不是覆盖旧对象

### Requirement: The system MUST manage document metadata and status in PostgreSQL
系统 MUST 在 PostgreSQL 中保存文档元数据，至少包括文档主键、归属用户、文档类型、显示名称、对象键、文件格式、文件大小、当前状态、创建时间、更新时间和删除标记。文档状态 MUST 明确区分上传生命周期和后续处理可用性。

#### Scenario: Upload completion creates a metadata record
- **WHEN** 客户端完成 OSS 上传并向服务端确认完成
- **THEN** 系统在 PostgreSQL 中创建或更新对应文档元数据记录，并将状态推进到已上传后的受控状态

#### Scenario: Document is not yet ready for downstream use
- **WHEN** 文档仅完成上传但尚未经过后续处理
- **THEN** 系统不会把该文档标记为可直接用于下游处理结果消费

### Requirement: The system MUST expose document listing and deletion under permission control
系统 MUST 提供受权限控制的文档列表和删除能力。用户 MUST 只能看到和管理自己有权限的文档；删除后，文档 MUST 不再出现在正常列表中，也 MUST 不再可用于面试准备或后续处理。

#### Scenario: User lists owned documents
- **WHEN** 用户查看自己的资料列表
- **THEN** 系统只返回该用户有权限访问的文档，并包含必要的文档类型与状态信息

#### Scenario: User deletes a document
- **WHEN** 用户删除自己拥有的文档
- **THEN** 系统将文档状态更新为删除态，并使其不再出现在默认可用列表中

#### Scenario: User attempts to delete another user's document
- **WHEN** 用户请求删除不属于自己的文档
- **THEN** 系统拒绝该操作，并返回统一权限错误

### Requirement: The system MUST reserve a processing handoff boundary without embedding processing logic
Document Service MUST 为后续 Document Processing Pipeline 预留受控交接边界，但 MUST NOT 在本能力中包含文档解析、Markdown 转换、Chunk、Embedding、向量数据库写入或 RAG 逻辑。文档服务只负责表达“是否已请求处理”“是否处理中”“是否已可用”这类生命周期事实。

#### Scenario: Newly uploaded document is handed off for later processing
- **WHEN** 文档上传完成并满足进入后续处理的条件
- **THEN** 系统能够通过受控状态或交接入口把该文档标记为待后续处理，而不直接执行解析逻辑

#### Scenario: Processing pipeline fails later
- **WHEN** 后续 Document Processing Pipeline 在独立实现中处理失败
- **THEN** 文档服务只更新文档处理状态为失败或不可用，而不是在本服务内暴露解析细节
