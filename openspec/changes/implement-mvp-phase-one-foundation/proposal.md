## Why

OfferSteady 现在已经有一套可验证用户流程的前端原型，但后续要进入 MVP 第一阶段开发，还缺少稳定的工程底座：后端尚未确定为正式应用框架，前端与服务端之间也还没有统一的通信层和可扩展模块边界。先完成这一阶段的基础工程，可以在保持现有页面结构和交互不变的前提下，把原型收束成可持续迭代的 MVP 工程。

## What Changes

- 新增 MVP 第一阶段工程基础变更，明确原型进入正式开发时的整体技术架构、目录分层和模块归属。
- 搭建 FastAPI 后端基础工程，包括应用入口、版本化路由、配置、依赖注入、健康检查和功能模块占位。
- 搭建 React Web 端与后端通信框架，在不改变现有页面结构和交互的前提下，引入统一 API 客户端、环境配置、错误归一化和数据访问边界。
- 为上传简历、上传 JD、知识库 / RAG、实时回答、截图回答、会话管理与桌面桥接预留后续模块，但本阶段不实现具体业务逻辑。
- **BREAKING**: 将当前以 TypeScript 原型服务为主的 `apps/api` 方向调整为 FastAPI 后端基础工程方向，后续 MVP 服务端实现以 Python / FastAPI 为主线推进。

## Capabilities

### New Capabilities
- `phase-one-architecture-baseline`: 定义 MVP 第一阶段工程的应用分层、目录模块、责任边界和原型保留约束
- `fastapi-backend-foundation`: 定义 FastAPI 后端基础工程必须提供的应用骨架、基础路由和模块占位
- `react-backend-communication-foundation`: 定义 React 原型在保持页面结构与交互不变时，如何接入统一的后端通信层
- `interview-feature-module-scaffolding`: 定义简历、JD、RAG、实时回答、截图回答等后续能力的预留模块与空实现边界

### Modified Capabilities
- None

## Impact

- Affected frontend: `apps/web` 的数据访问层、环境配置、适配器边界与后续 API 接入方式
- Affected backend: 当前 `apps/api` 原型服务方向、未来 FastAPI 工程目录、基础运行与测试方式
- Affected shared modules: `packages/protocol`、未来共享 DTO / contract、错误模型与会话协议
- Affected docs: `docs/architecture.md`、后续开发说明与运行文档
- Affected future features: 简历上传、JD 上传、知识库 / RAG、实时回答、截图回答、桌面桥接和计费服务的后续实现切片
