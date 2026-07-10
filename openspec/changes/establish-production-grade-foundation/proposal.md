## Why

OfferSteady 现在已经有原型和 MVP 第一阶段工程骨架，但距离可持续承载后续所有业务模块的“生产级统一底座”还差一层明确的工程规范与部署基础。现在先把 React、FastAPI、PostgreSQL、pgvector、阿里云 OSS、Docker、Nginx、环境变量、配置、日志、异常和响应规范统一下来，后续每个业务变更就不需要反复各自搭底层。

## What Changes

- 建立面向生产部署的统一基础工程方案，覆盖 React + TypeScript 前端、FastAPI 后端、PostgreSQL、pgvector、阿里云 OSS、Docker 与 Nginx 的职责边界和协作方式。
- 统一环境变量管理、配置分层、日志规范、模块目录结构和基础开发/部署约定。
- 定义服务端 API 规范，包括版本化路径、统一响应结构、统一异常处理、错误码与基础中间件边界。
- 定义容器化与反向代理基础方案，为本地开发、测试环境和生产环境提供一致的运行基线。
- 不实现任何具体业务逻辑，只实现生产级基础工程、基础配置与统一规范。

## Capabilities

### New Capabilities
- `production-runtime-foundation`: 定义 React、FastAPI、PostgreSQL、pgvector、OSS、环境变量、配置、日志和模块目录的统一生产级工程底座
- `api-platform-standards`: 定义版本化 API、统一响应结构、统一异常处理、错误模型和基础服务约束
- `containerized-deployment-baseline`: 定义 Docker、Nginx、多服务运行方式和环境间部署基线

### Modified Capabilities
- None

## Impact

- Affected frontend: `apps/web` 的工程组织、环境配置、构建与部署接入方式
- Affected backend: `apps/backend` 的配置、日志、异常、API schema、目录规范和数据层接入方式
- Affected infra: PostgreSQL、pgvector、阿里云 OSS、Docker、Nginx 和多环境配置管理
- Affected shared modules: `packages/` 下的共享协议、配置常量、错误模型与公共工具
- Affected operations: 本地开发、CI、容器构建、部署与运行排障方式
