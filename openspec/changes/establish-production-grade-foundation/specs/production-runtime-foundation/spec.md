## ADDED Requirements

### Requirement: The project MUST provide one production-grade baseline across web, backend, data, storage and shared modules
系统 MUST 建立统一的生产级基础工程结构，覆盖 `React + TypeScript` Web 应用、`FastAPI` 后端、`PostgreSQL`、`pgvector`、阿里云 OSS 和共享模块目录。该结构 MUST 明确应用、共享包、配置、脚本、部署资产和测试资产的职责边界，并 MUST 避免把业务逻辑散落到基础设施目录中。

#### Scenario: Developer inspects the repository layout
- **WHEN** 开发者查看项目目录与工程说明
- **THEN** 可以清楚区分前端应用、后端应用、共享模块、基础设施配置、部署资源和测试资源的职责

#### Scenario: New business module is introduced later
- **WHEN** 后续新增简历、JD、RAG、实时回答或截图回答模块
- **THEN** 新模块可以落入既定目录规范与依赖边界中，而不需要重新定义基础工程结构

### Requirement: Environment variables and application configuration MUST be centrally managed
系统 MUST 为前端、后端、数据库、对象存储和部署环境提供统一的环境变量与配置管理机制。配置 MUST 支持按环境分层，例如本地开发、测试、预发和生产；敏感密钥 MUST NOT 写死在客户端代码、普通脚本或仓库默认常量中。

#### Scenario: Backend starts in production mode
- **WHEN** 后端以生产环境配置启动
- **THEN** 数据库、pgvector、OSS、日志和运行参数都从受控配置源读取，而不是依赖硬编码默认值

#### Scenario: Frontend is built for a public environment
- **WHEN** Web 应用构建发布版本
- **THEN** 只暴露允许下发到客户端的公开配置，服务端密钥与存储凭证不会出现在浏览器配置中

### Requirement: Logging and diagnostics MUST follow a unified baseline
系统 MUST 提供统一日志管理基线，至少覆盖结构化日志字段、请求关联、错误分类、环境标签和敏感字段脱敏要求。日志规范 SHALL 同时适用于 FastAPI 服务、后台任务进程和反向代理接入层；前端仅保留必要的调试与错误上报边界。

#### Scenario: API request fails
- **WHEN** 某个后端请求抛出异常或返回错误
- **THEN** 系统输出结构化日志，包含请求上下文与错误分类，同时不记录简历正文、JD 正文、截图内容或长期凭证

#### Scenario: Operator investigates a multi-service issue
- **WHEN** 运维或开发排查 Web、API、数据库与对象存储之间的问题
- **THEN** 可以通过统一请求标识与一致日志字段串联跨组件诊断信息
