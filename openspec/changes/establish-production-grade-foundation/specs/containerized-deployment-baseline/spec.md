## ADDED Requirements

### Requirement: The project MUST define one containerized deployment baseline for local and production-like environments
系统 MUST 提供统一的容器化运行基线，覆盖 Web 构建产物、FastAPI 服务、PostgreSQL、pgvector 扩展和必要的基础依赖。该基线 SHALL 支持本地联调与生产相近环境的一致启动方式，并 MUST 明确服务之间的网络、端口、卷和健康检查约定。

#### Scenario: Developer boots the stack locally
- **WHEN** 开发者按项目文档启动容器化环境
- **THEN** 可以以一致方式启动前端、后端、数据库和代理层，而不需要逐个手工拼接依赖

#### Scenario: Deployment environment provisions the stack
- **WHEN** 项目部署到测试或生产相近环境
- **THEN** 基础服务拓扑、依赖顺序和健康检查规则与本地容器基线保持一致

### Requirement: Nginx MUST provide one standardized ingress role
系统 MUST 为 Nginx 定义统一入口职责，例如静态资源分发、反向代理、压缩、基础缓存策略、请求头透传和上游转发边界。Nginx MUST NOT 承载业务逻辑，但 MUST 为 Web 与 API 提供一致的入口组织方式。

#### Scenario: Browser requests the web application
- **WHEN** 用户访问产品入口
- **THEN** Nginx 按统一规则分发前端静态资源，并把 API 请求转发到后端服务

#### Scenario: API is called through the public domain
- **WHEN** 客户端通过统一域名访问 API
- **THEN** 反向代理保留必要请求头与请求标识，并按统一上游规则转发到 FastAPI

### Requirement: Shared deployment assets MUST describe storage and data-service dependencies without embedding secrets
系统 MUST 在容器与部署基线中明确 PostgreSQL、pgvector 和阿里云 OSS 的依赖位置、连接方式和运行前提，但 MUST NOT 在仓库内嵌入生产密钥、数据库密码或可直接使用的 OSS 凭证。部署资产 SHALL 说明这些依赖如何通过环境变量或密钥管理系统注入。

#### Scenario: Operator prepares production configuration
- **WHEN** 运维为生产环境准备部署变量
- **THEN** 可以根据统一部署说明注入数据库、向量扩展和 OSS 配置，而无需修改应用源码

#### Scenario: Repository is reviewed for secret safety
- **WHEN** 团队审查 Docker、Nginx 和部署配置
- **THEN** 仓库中不存在硬编码的生产密码、对象存储密钥或数据库凭证
