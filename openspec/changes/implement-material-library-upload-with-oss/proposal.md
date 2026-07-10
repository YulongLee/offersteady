## Why

当前资料库页面已经有较完整的原型交互，但后端仍只有占位接口，无法真正完成简历、JD、知识资料的上传、格式校验、对象存储落盘和后续处理状态流转。现在补齐这部分 MVP 方案，可以把“可演示原型”推进为“可接真实资料上传链路”的下一阶段基础能力，同时为后续解析、RAG、面试准备选择与删除治理打好边界。

## What Changes

- 为简历、职位 JD、知识资料新增一套可实现的资料上传方案，覆盖前端发起上传、服务端签发上传意图、阿里云 OSS 存储、上传完成确认和资料元数据登记。
- 统一定义当前支持的文件格式校验规则，前端与后端都基于同一份受支持类型约束 `pdf/docx/doc/txt/md`。
- 为上传后的资料引入明确的服务端处理状态流，包括待上传、上传中、已上传待处理、处理中、就绪、失败、已删除。
- 区分“文件上传链路”和“JD 粘贴文本链路”，避免把文本粘贴能力和 OSS 文件能力混为一谈。
- 为后续解析、索引、RAG 和面试资料选择预留稳定模块边界，但本变更不直接实现完整解析或检索逻辑。

## Capabilities

### New Capabilities
- `material-upload-pipeline`: 定义资料库文件上传、OSS 存储、服务端校验、完成确认和处理状态的统一行为

### Modified Capabilities
- None

## Impact

- Affected frontend: `apps/web` 资料页上传入口、上传状态管理、API 通信层、格式校验复用
- Affected backend: `apps/backend` 的 `resume`、`job_description`、`knowledge` 模块、存储端口、上传 schema 与处理任务边界
- Affected dependencies: 阿里云 OSS SDK / 签名能力、服务端配置管理、对象键命名策略
- Affected systems: 资料元数据存储、对象存储、后续解析 / 索引异步任务链路
- No scope change to live interview UX: 不改变当前原型里的面试准备、资料选择和实时回答页面结构
